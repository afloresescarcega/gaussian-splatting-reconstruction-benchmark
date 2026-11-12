"""v5 faithfulness scorer.

score_v5.py <ply> <cameras.json> <set_dir> <name_map.tsv> <out_dir>
  set_dir holds images/ (contestant views, DSC*.jpg), heldout/ (DSC*.jpg + poses_bounds.npy).
  name_map.tsv: "<uploaded name>\t<DSC id>".

Steps: parse the .ply (standard 3DGS fields) and cameras.json (lenient parser), convert cameras to
OpenCV c2w, Sim(3)-align registered camera centres to the COLMAP GT (Umeyama), render the .ply at the
6 held-out GT poses with our own EWA tile rasterizer (front-to-back alpha blending, black background),
and report LPIPS (alex), SSIM, PSNR. Also re-renders each registered *input* view at the contestant's
own camera to recompute input-view PSNR (honesty check vs the app panel).
No sky mask: the garden held-out views contain almost no sky.
"""
import json, math, os, re, sys
import numpy as np
import torch
from PIL import Image
from plyfile import PlyData

RES_W = 500  # render width; height from aspect
C0 = 0.28209479177387814
torch.set_grad_enabled(False)


# ---------------------------------------------------------------- GT
def load_gt(set_dir):
    pb = np.load(os.path.join(set_dir, 'heldout', 'poses_bounds.npy'))
    P = pb[:, :15].reshape(-1, 3, 5)
    h, w, f = P[0, :, 4]
    gt = {}
    for i in range(P.shape[0]):
        m = P[i, :, :4]  # LLFF columns: [down, right, back]
        R = np.stack([m[:, 1], m[:, 0], -m[:, 2]], 1)  # -> OpenCV [right, down, forward]
        c2w = np.eye(4); c2w[:3, :3] = R; c2w[:3, 3] = m[:, 3]
        gt['DSC%05d' % (7956 + i)] = c2w
    return gt, (h, w, f)


# ---------------------------------------------------------------- PLY
def load_ply(path):
    v = PlyData.read(path)['vertex']
    names = v.data.dtype.names
    g = lambda k: np.asarray(v[k], np.float64)
    xyz = np.stack([g('x'), g('y'), g('z')], 1)
    notes = []
    if all(f'scale_{i}' in names for i in range(3)):
        s = np.stack([g(f'scale_{i}') for i in range(3)], 1)
        if s.min() < 0 or s.max() > 3:  # log-space (as the prompt asks)
            scale = np.exp(s)
        else:
            scale = s; notes.append('scale looks linear (all in [0,3]); used as-is')
    else:
        scale = np.full((len(xyz), 3), 0.01); notes.append('no scale fields')
    if all(f'rot_{i}' in names for i in range(4)):
        q = np.stack([g(f'rot_{i}') for i in range(4)], 1)
    else:
        q = np.tile([1, 0, 0, 0], (len(xyz), 1)).astype(float); notes.append('no rot fields')
    q = q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-12)
    if 'opacity' in names:
        o = g('opacity')
        if o.min() < 0 or o.max() > 1:
            op = 1 / (1 + np.exp(-o))
        else:
            op = o; notes.append('opacity looks linear [0,1]; used as-is')
    else:
        op = np.ones(len(xyz)); notes.append('no opacity')
    if all(f'f_dc_{i}' in names for i in range(3)):
        col = 0.5 + C0 * np.stack([g(f'f_dc_{i}') for i in range(3)], 1)
    elif all(k in names for k in ('red', 'green', 'blue')):
        col = np.stack([g('red'), g('green'), g('blue')], 1) / 255.0; notes.append('rgb fields, not SH-DC')
    else:
        col = np.full((len(xyz), 3), 0.5); notes.append('no colour')
    ok = np.isfinite(xyz).all(1) & np.isfinite(scale).all(1) & np.isfinite(q).all(1) & np.isfinite(op) & np.isfinite(col).all(1)
    return dict(xyz=xyz[ok], scale=scale[ok], q=q[ok], op=np.clip(op[ok], 0, 1), col=np.clip(col[ok], 0, 1),
                n=int(ok.sum()), n_raw=len(xyz), fields=list(names), notes=notes)


# ---------------------------------------------------------------- cameras.json
def _find_list(o):
    if isinstance(o, list) and o and isinstance(o[0], dict): return o
    if isinstance(o, dict):
        for k in ('cameras', 'images', 'views', 'frames', 'items'):
            if k in o and isinstance(o[k], (list, dict)):
                r = _find_list(o[k]) if isinstance(o[k], list) else [dict(v, name=n) if isinstance(v, dict) else v for n, v in o[k].items()]
                if r: return r
        vals = list(o.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return [dict(v, name=n) for n, v in o.items()]
    return None


def _get(d, *keys):
    for k in keys:
        if k in d: return d[k]
    for v in d.values():
        if isinstance(v, dict):
            r = _get(v, *keys)
            if r is not None: return r
    return None


def _mat4(m):
    a = np.asarray(m, float)
    if a.size == 16: a = a.reshape(4, 4)
    elif a.size == 12: a = np.vstack([a.reshape(3, 4), [0, 0, 0, 1]])
    else: return None
    if np.allclose(a[3], [0, 0, 0, 1]) or not np.allclose(a[:, 3][:3], 0): return a
    return a.T  # column-major flat


def load_cameras(path):
    o = json.load(open(path))
    raw = json.dumps(o).lower()
    lst = _find_list(o) or []
    gl = bool(re.search(r'opengl|\+y up|-z forward|y up|three\.?js', raw)) and not re.search(r'"?opencv"?', raw)
    cams = []
    for d in lst:
        name = _get(d, 'file_name', 'filename', 'fileName', 'name', 'image', 'file', 'image_name', 'imageName')
        reg = _get(d, 'registered')
        reg = True if reg is None else bool(reg)
        m = _get(d, 'camera_to_world', 'cameraToWorld', 'c2w', 'transform_matrix', 'camToWorld', 'matrix', 'pose', 'extrinsics_c2w')
        w2c = None
        if m is None:
            w2c = _get(d, 'world_to_camera', 'w2c', 'worldToCamera', 'extrinsics', 'viewMatrix')
        K = _get(d, 'intrinsics', 'K')
        fx = _get(d, 'fx'); fy = _get(d, 'fy'); cx = _get(d, 'cx'); cy = _get(d, 'cy')
        if isinstance(K, (list, tuple)) and np.asarray(K).size == 9:
            Kk = np.asarray(K, float).reshape(3, 3); fx, fy, cx, cy = Kk[0, 0], Kk[1, 1], Kk[0, 2], Kk[1, 2]
        W = _get(d, 'width', 'w', 'image_width'); H = _get(d, 'height', 'h', 'image_height')
        c2w = None
        if m is not None: c2w = _mat4(m)
        elif w2c is not None:
            a = _mat4(w2c); c2w = np.linalg.inv(a) if a is not None else None
        if c2w is not None and gl:
            c2w = c2w @ np.diag([1, -1, -1, 1])
        cams.append(dict(name=str(name) if name else None, registered=reg and c2w is not None, c2w=c2w,
                         fx=fx, fy=fy, cx=cx, cy=cy, W=W, H=H))
    return cams, dict(convention='opengl->flipped' if gl else 'opencv (assumed)', n=len(cams))


# ---------------------------------------------------------------- Sim(3)
def umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0: S[2, 2] = -1
    R = U @ S @ Vt
    var = (xs ** 2).sum() / len(src)
    s = np.trace(np.diag(D) @ S) / var
    t = mu_d - s * R @ mu_s
    return s, R, t


# ---------------------------------------------------------------- rasterizer
def quat_to_R(q):
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    return torch.stack([
        1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
        2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
        2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], 1).reshape(-1, 3, 3)


def render(G, c2w, fx, fy, cx, cy, W, H, tile=16, bg=0.0):
    dev = 'cpu'; f = torch.float32
    w2c = np.linalg.inv(c2w)
    Rw = torch.tensor(w2c[:3, :3], dtype=f); tw = torch.tensor(w2c[:3, 3], dtype=f)
    m = torch.tensor(G['xyz'], dtype=f)
    pc = m @ Rw.T + tw
    z = pc[:, 2]
    keep = z > 0.01
    if keep.sum() == 0: return np.full((H, W, 3), bg, np.float32), 0
    idx = torch.nonzero(keep).squeeze(1)
    pc = pc[idx]; z = z[idx]
    S = torch.tensor(G['scale'], dtype=f)[idx]
    Rg = quat_to_R(torch.tensor(G['q'], dtype=f)[idx])
    M = Rg * S[:, None, :]
    cov = M @ M.transpose(1, 2)
    covc = Rw @ cov @ Rw.T
    x, y = pc[:, 0], pc[:, 1]
    J = torch.zeros(len(idx), 2, 3)
    J[:, 0, 0] = fx / z; J[:, 0, 2] = -fx * x / z ** 2
    J[:, 1, 1] = fy / z; J[:, 1, 2] = -fy * y / z ** 2
    c2 = J @ covc @ J.transpose(1, 2)
    c2[:, 0, 0] += 0.3; c2[:, 1, 1] += 0.3
    a, b, c = c2[:, 0, 0], c2[:, 0, 1], c2[:, 1, 1]
    det = a * c - b * b
    good = det > 1e-12
    u = fx * x / z + cx; v = fy * y / z + cy
    mid = 0.5 * (a + c); lam = mid + torch.sqrt(torch.clamp(mid * mid - det, min=0.1))
    r = torch.ceil(3 * torch.sqrt(lam))
    good &= (u + r > 0) & (u - r < W) & (v + r > 0) & (v - r < H) & (r < 4 * max(W, H))
    sel = torch.nonzero(good).squeeze(1)
    if len(sel) == 0: return np.full((H, W, 3), bg, np.float32), 0
    u, v, r, z = u[sel], v[sel], r[sel], z[sel]
    conA, conB, conC = (c / det)[sel], (-b / det)[sel], (a / det)[sel]
    op = torch.tensor(G['op'], dtype=f)[idx][sel]; col = torch.tensor(G['col'], dtype=f)[idx][sel]
    TX, TY = (W + tile - 1) // tile, (H + tile - 1) // tile
    x0 = torch.clamp(((u - r) // tile).long(), 0, TX - 1); x1 = torch.clamp(((u + r) // tile).long(), 0, TX - 1)
    y0 = torch.clamp(((v - r) // tile).long(), 0, TY - 1); y1 = torch.clamp(((v + r) // tile).long(), 0, TY - 1)
    order = torch.argsort(z)
    out = torch.full((H, W, 3), bg)
    # bucket gaussians by tile (in depth order)
    nx, ny = (x1 - x0 + 1), (y1 - y0 + 1)
    cnt = nx * ny
    if cnt.sum() > 6e7: raise RuntimeError('too many tile pairs')
    gi = torch.repeat_interleave(torch.arange(len(sel)), cnt)
    off = torch.arange(int(cnt.sum())) - torch.repeat_interleave(torch.cumsum(cnt, 0) - cnt, cnt)
    tx = x0[gi] + off % nx[gi]; ty = y0[gi] + off // nx[gi]
    tid = ty * TX + tx
    rank = torch.empty_like(order); rank[order] = torch.arange(len(order))
    key = tid * len(sel) + rank[gi]
    srt = torch.argsort(key)
    tid_s, gi_s = tid[srt], gi[srt]
    bounds = torch.searchsorted(tid_s, torch.arange(TX * TY + 1))
    py, px = torch.meshgrid(torch.arange(tile, dtype=f), torch.arange(tile, dtype=f), indexing='ij')
    for t in range(TX * TY):
        s0, s1 = int(bounds[t]), int(bounds[t + 1])
        if s0 == s1: continue
        g = gi_s[s0:s1]
        txx, tyy = t % TX, t // TX
        X = (px.reshape(-1) + txx * tile + 0.5)[:, None]; Y = (py.reshape(-1) + tyy * tile + 0.5)[:, None]
        dx = X - u[g][None]; dy = Y - v[g][None]
        pw = -0.5 * (conA[g][None] * dx * dx + conC[g][None] * dy * dy) - conB[g][None] * dx * dy
        al = torch.clamp(op[g][None] * torch.exp(torch.clamp(pw, max=0)), max=0.99)
        al = torch.where(al < 1 / 255, torch.zeros_like(al), al)
        T = torch.cumprod(torch.cat([torch.ones(al.shape[0], 1), 1 - al[:, :-1]], 1), 1)
        wgt = T * al
        rgb = wgt @ col[g] + (T[:, -1:] * (1 - al[:, -1:])) * bg
        rgb = rgb.reshape(tile, tile, 3)
        ye, xe = min(tile, H - tyy * tile), min(tile, W - txx * tile)
        out[tyy * tile: tyy * tile + ye, txx * tile: txx * tile + xe] = rgb[:ye, :xe]
    return out.clamp(0, 1).numpy(), int(len(sel))


# ---------------------------------------------------------------- metrics
_lp = None
def metrics(pred, gt):
    global _lp
    from skimage.metrics import structural_similarity
    import lpips
    if _lp is None: _lp = lpips.LPIPS(net='alex', verbose=False)
    mse = float(((pred - gt) ** 2).mean())
    psnr = 10 * math.log10(1 / max(mse, 1e-10))
    ssim = float(structural_similarity(pred, gt, channel_axis=2, data_range=1.0))
    tp = lambda a: torch.tensor(a).permute(2, 0, 1)[None].float() * 2 - 1
    lp = float(_lp(tp(pred), tp(gt)).item())
    return dict(psnr=round(psnr, 2), ssim=round(ssim, 4), lpips=round(lp, 4))


def load_img(p, W, H):
    return np.asarray(Image.open(p).convert('RGB').resize((W, H), Image.BICUBIC), np.float32) / 255


HELDOUT = ['DSC08022', 'DSC07957', 'DSC08117', 'DSC08061', 'DSC07999', 'DSC08003']


def main(ply, camf, set_dir, name_map, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    nm = dict(l.rstrip('\n').split('\t') for l in open(name_map) if l.strip())
    gt, (h0, w0, f0) = load_gt(set_dir)
    res = dict(ply=os.path.basename(ply), cameras=os.path.basename(camf) if camf else None)
    G = load_ply(ply); res.update(n_gaussians=G['n'], n_raw=G['n_raw'], ply_notes=G['notes'])
    sc = G['scale']; res['scale_anisotropy_median'] = round(float(np.median(sc.max(1) / np.maximum(sc.min(1), 1e-9))), 3)
    res['rot_identity_frac'] = round(float((np.abs(G['q'][:, 0]) > 0.9999).mean()), 4)
    cams, cinfo = (load_cameras(camf) if camf and os.path.exists(camf) else ([], dict(convention=None, n=0)))
    res['cameras_info'] = cinfo
    reg = []
    for c in cams:
        if not c['registered'] or not c['name']: continue
        base = os.path.basename(c['name'])
        dsc = nm.get(base) or nm.get(base.split('?')[0])
        if dsc and dsc in gt: reg.append((c, dsc))
    res['views_registered'] = f'{len(reg)} / 7'
    W = RES_W; H = int(round(W * 1296 / 2000))
    k = W / w0; fxg = f0 * k
    # input-view self-consistency PSNR (contestant's own cameras + intrinsics)
    iv = {}
    for c, dsc in reg:
        cw, ch = c['W'] or 2000, c['H'] or 1296
        try:
            sx = W / float(cw); sy = H / float(ch)
            fx = float(c['fx']) * sx; fy = float(c['fy'] or c['fx']) * sy
            cx = float(c['cx'] if c['cx'] is not None else cw / 2) * sx; cy = float(c['cy'] if c['cy'] is not None else ch / 2) * sy
            img, _ = render(G, c['c2w'], fx, fy, cx, cy, W, H)
            iv[dsc] = metrics(img, load_img(os.path.join(set_dir, 'images', dsc + '.jpg'), W, H))['psnr']
        except Exception as e:
            iv[dsc] = f'err: {e}'[:80]
    res['input_view_psnr_ours'] = iv
    nums = [v for v in iv.values() if isinstance(v, float)]
    res['input_view_psnr_ours_mean'] = round(float(np.mean(nums)), 2) if nums else None
    if len(reg) < 3:
        res['heldout'] = None; res['note'] = 'fewer than 3 registered views: no Sim(3) alignment'
        json.dump(res, open(os.path.join(out_dir, 'score.json'), 'w'), indent=2); print(json.dumps(res)); return res
    src = np.stack([c['c2w'][:3, 3] for c, _ in reg]); dst = np.stack([gt[d][:3, 3] for _, d in reg])
    if np.linalg.norm(src - src.mean(0), axis=1).max() < 1e-6:
        res['heldout'] = None; res['note'] = 'degenerate: all registered camera centres coincide (rotation-only poses); no Sim(3) alignment possible'
        json.dump(res, open(os.path.join(out_dir, 'score.json'), 'w'), indent=2); print(json.dumps(res)[:400]); return res
    s, R, t = umeyama(src, dst)
    resid = np.linalg.norm((s * (R @ src.T)).T + t - dst, axis=1)
    spread = np.linalg.norm(dst - dst.mean(0), axis=1).mean()
    res['sim3'] = dict(scale=round(float(s), 5), center_rmse_rel=round(float(np.sqrt((resid ** 2).mean()) / spread), 4))
    rot_err = []
    for c, d in reg:
        Rc = R @ c['c2w'][:3, :3]; Rg = gt[d][:3, :3]
        rot_err.append(math.degrees(math.acos(np.clip((np.trace(Rc.T @ Rg) - 1) / 2, -1, 1))))
    res['sim3']['rot_err_deg_median'] = round(float(np.median(rot_err)), 2)
    per = {}
    for d in HELDOUT:
        cg = gt[d]
        Rc = R.T @ cg[:3, :3]; cc = R.T @ (cg[:3, 3] - t) / s
        c2w = np.eye(4); c2w[:3, :3] = Rc; c2w[:3, 3] = cc
        img, nvis = render(G, c2w, fxg, fxg, W / 2, H / 2, W, H)
        g = load_img(os.path.join(set_dir, 'heldout', d + '.jpg'), W, H)
        mtr = metrics(img, g); mtr['visible'] = nvis; per[d] = mtr
        Image.fromarray((img * 255).astype(np.uint8)).save(os.path.join(out_dir, f'heldout_{d}.png'))
    res['heldout'] = per
    res['heldout_mean'] = {k: round(float(np.mean([p[k] for p in per.values()])), 4) for k in ('lpips', 'ssim', 'psnr')}
    json.dump(res, open(os.path.join(out_dir, 'score.json'), 'w'), indent=2)
    print(json.dumps({k: res[k] for k in ('n_gaussians', 'views_registered', 'sim3', 'heldout_mean', 'input_view_psnr_ours_mean')}))
    return res


def baselines(set_dir, out_dir):
    """(a) mean colour of the 7 inputs; (n) nearest input photo shown unwarped (GT camera distance)."""
    os.makedirs(out_dir, exist_ok=True)
    gt, _ = load_gt(set_dir)
    W = RES_W; H = int(round(W * 1296 / 2000))
    ins = sorted(f[:-4] for f in os.listdir(os.path.join(set_dir, 'images')) if f.endswith('.jpg'))
    imgs = {d: load_img(os.path.join(set_dir, 'images', d + '.jpg'), W, H) for d in ins}
    mean = np.mean([i.reshape(-1, 3).mean(0) for i in imgs.values()], 0)
    out = {'mean_colour': {}, 'nearest_input': {}}
    for d in HELDOUT:
        g = load_img(os.path.join(set_dir, 'heldout', d + '.jpg'), W, H)
        out['mean_colour'][d] = metrics(np.broadcast_to(mean, g.shape).astype(np.float32).copy(), g)
        nn = min(ins, key=lambda k: np.linalg.norm(gt[k][:3, 3] - gt[d][:3, 3]))
        out['nearest_input'][d] = dict(metrics(imgs[nn], g), src=nn)
    for k in list(out):
        out[k + '_mean'] = {m: round(float(np.mean([p[m] for p in out[k].values()])), 4) for m in ('lpips', 'ssim', 'psnr')}
    json.dump(out, open(os.path.join(out_dir, 'baselines.json'), 'w'), indent=2)
    print(json.dumps({k: v for k, v in out.items() if k.endswith('_mean')}))


if __name__ == '__main__':
    if sys.argv[1] == '--baselines': baselines(sys.argv[2], sys.argv[3])
    else: main(*sys.argv[1:6])
