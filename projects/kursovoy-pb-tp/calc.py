"""Расчёты курсового проекта «Пожарная безопасность технологических процессов».

Вариант зачётки 73, фамилия Смолин. Аппарат: смеситель растворителя,
растворитель Р-4, помещение цеха мерников и растворителей, г. Новосибирск.
Все числа документа берутся из результата run() — менять исходные данные
нужно только в блоке INPUT.
"""
import math

# ----------------------------------------------------------------- INPUT ---
INPUT = dict(
    variant="73",
    surname="Смолин",
    region="г. Новосибирск",
    t_air_max=38.0,          # °C, абс. максимум (СП 131.13330) — ПРОВЕРИТЬ по своему изданию
    room=dict(a=13.0, b=9.2, h=3.5),          # табл. 3.1, вариант 7
    mixer=dict(V=0.7, eps=0.9, L_in=2.0, L_out=4.0, d_mm=50.0,
               q_lps=2.3, t_tech=22.0, P_mpa=0.35, u=0.5, A=8.0,
               shutdown="manual"),            # табл. 3.3, блок «Смесители», колонка 3
    composition={"toluene": 0.62, "acetone": 0.26, "butylacetate": 0.12},  # Р-4, % масс.
    hazard="acetone",        # наиболее опасное вещество (min t_всп) — по нему ведутся расчёты
    P0=101.325,              # кПа
)

# Справочные данные: М, tвсп, tсв (прил. 10 методички); константы Антуана
# (прил. 10, P в кПа, t в °C); Qн — теплота сгорания, кДж/кг (прил. 10);
# НКПР/ВКПР, % об. и плотность жидкости — справочные (Корольченко, ВНИИПО).
COMP = {
    "acetone": dict(name="Ацетон", formula="C3H6O", nC=3, nH=6, nO=1, M=58.08,
                    t_flash=-18, t_auto=535, A=6.37551, B=1281.721, C=237.088,
                    Qn=31360, lel=2.7, uel=13.0, rho=791.0, tn_ref=-20.0, tv_ref=6.0),
    "toluene": dict(name="Толуол", formula="C7H8", nC=7, nH=8, nO=0, M=92.14,
                    t_flash=7, t_auto=535, A=6.0507, B=1328.171, C=217.713,
                    Qn=40936, lel=1.27, uel=7.0, rho=867.0),
    "butylacetate": dict(name="н-Бутилацетат", formula="C6H12O2", nC=6, nH=12, nO=2,
                         M=116.16, t_flash=29, t_auto=330, A=6.25205, B=1430.418,
                         C=210.745, Qn=28280, lel=1.35, uel=7.5, rho=882.0),
}


# -------------------------------------------------------------- helpers ----
def p_sat(c, t):
    """Давление насыщенного пара компонента, кПа (уравнение Антуана)."""
    return 10 ** (c["A"] - c["B"] / (t + c["C"]))


def t_from_p(c, p):
    """Температура (°C), при которой давление насыщенного пара равно p, кПа."""
    return c["B"] / (c["A"] - math.log10(p)) - c["C"]


def molar_volume(t, P=101.325):
    """Мольный объём газа при t °C и давлении P, кПа (ф. 10), м³/кмоль."""
    return 22.4135 * (273.0 + t) / 273.0 * (101.325 / P)


def bisect(f, lo, hi, n=100):
    flo = f(lo)
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------- свойства смеси ----
def mixture():
    """Р-4 как раствор: мольные доли, плотность, состав пара, пределы."""
    w = INPUT["composition"]
    n = {k: w[k] / COMP[k]["M"] for k in w}
    sn = sum(n.values())
    x = {k: n[k] / sn for k in w}                        # мольные доли жидкости
    rho = 1.0 / sum(w[k] / COMP[k]["rho"] for k in w)    # кг/м³, аддитивность объёмов
    M_liq = 1.0 / sn                                     # кг/кмоль, «средняя» молярная масса
    vol = {k: w[k] / COMP[k]["rho"] * rho for k in w}    # объёмные доли компонентов
    return dict(w=w, x=x, rho=rho, M_liq=M_liq, vol=vol)


def vapor(t, mix=None):
    """Насыщенный пар наиболее опасного вещества (INPUT['hazard']) при t, °C."""
    h = INPUT["hazard"]
    c = COMP[h]
    ps = p_sat(c, t)
    return dict(p={h: ps}, ps=ps, y={h: 1.0}, lel=c["lel"], uel=c["uel"], M=c["M"],
                phi=100.0 * ps / INPUT["P0"])          # при 101,3 кПа, % об.


def vapor_mix(t, mix=None):
    """Пар над раствором Р-4 (закон Рауля, правило Ле Шателье) — справочно."""
    mix = mix or mixture()
    p = {k: mix["x"][k] * p_sat(COMP[k], t) for k in COMP}
    ps = sum(p.values())
    y = {k: p[k] / ps for k in p}
    lel = 1.0 / sum(y[k] / COMP[k]["lel"] for k in y)
    uel = 1.0 / sum(y[k] / COMP[k]["uel"] for k in y)
    return dict(p=p, ps=ps, y=y, lel=lel, uel=uel, M=sum(y[k] * COMP[k]["M"] for k in y),
                phi=100.0 * ps / INPUT["P0"])


def temp_limits(mix=None):
    """Температурные пределы распространения пламени наиболее опасного вещества, °C (справочные)."""
    c = COMP[INPUT["hazard"]]
    return c["tn_ref"], c["tv_ref"]


def component_limits():
    """Температурные пределы компонентов: справочные (если есть) или по Антуану (ф. 33, 34)."""
    out = {}
    for k, c in COMP.items():
        if "tn_ref" in c:
            out[k] = (c["tn_ref"], c["tv_ref"])
            continue
        tn = t_from_p(c, c["lel"] / 100 * INPUT["P0"])
        tv = t_from_p(c, c["uel"] / 100 * INPUT["P0"])
        out[k] = (tn, tv)
    return out


def stoich(mix, y):
    """β и Cст (% об.) паровой смеси: Cст = 100/(1+4,84β), β = nC + nH/4 − nO/2."""
    beta = sum(y[k] * (COMP[k]["nC"] + COMP[k]["nH"] / 4 - COMP[k]["nO"] / 2) for k in y)
    return beta, 100.0 / (1 + 4.84 * beta)


# ------------------------------------------------ η по таблице 7.1 (прил. 7) --
ETA_T = [10, 15, 20, 30, 35]
ETA = {0.0: [1.0] * 5, 0.1: [3.0, 2.6, 2.4, 1.8, 1.6], 0.2: [4.6, 3.8, 3.5, 2.4, 2.3],
       0.5: [6.6, 5.7, 5.4, 3.6, 3.2], 1.0: [10.0, 8.7, 7.7, 5.6, 4.6]}


def eta(u, t):
    row = ETA[min(ETA, key=lambda k: abs(k - u))]
    if t >= ETA_T[-1]:
        return row[-1]          # выше 35 °C принимаем значение при 35 °C
    if t <= ETA_T[0]:
        return row[0]
    for i in range(len(ETA_T) - 1):
        if ETA_T[i] <= t <= ETA_T[i + 1]:
            k = (t - ETA_T[i]) / (ETA_T[i + 1] - ETA_T[i])
            return row[i] + k * (row[i + 1] - row[i])


# ------------------------------------------------------ раздел 3 (аппарат) --
def inside():
    """Горючая среда внутри смесителя (табл. 4.3, прил. 5)."""
    mix = mixture()
    mx = INPUT["mixer"]
    tn, tv = temp_limits(mix)
    t = mx["t_tech"]
    Pp = mx["P_mpa"] * 1000.0                      # кПа абс.
    v = vapor(t, mix)
    phi_p = 100.0 * v["ps"] / Pp                   # % об. в ПВП при рабочем давлении (ф. 12)
    Vap = mx["V"]
    Vzh = Vap * mx["eps"]
    return dict(mix=mix, tn=tn, tv=tv, t=t, Pp=Pp, v=v, phi_p=phi_p,
                Vap=Vap, Vzh=Vzh, Vpvp=Vap - Vzh,
                normal=(tn - 10 <= t <= tv + 15),
                start=(t >= tn),
                stop=(tn <= t <= tv),
                lel=v["lel"], uel=v["uel"], in_conc=(v["lel"] <= phi_p <= v["uel"]))


def outside():
    """Горючая среда снаружи смесителя (табл. 4.5): загрузка через люк, утечки."""
    R = INPUT["room"]
    mx = INPUT["mixer"]
    ins = inside()
    mix, v, t = ins["mix"], ins["v"], ins["t"]
    Vroom = R["a"] * R["b"] * R["h"]
    Vsv = 0.8 * Vroom
    Pp_pa = ins["Pp"] * 1000.0
    P0_pa = INPUT["P0"] * 1000.0
    phi_s = v["ps"] * 1000.0 / Pp_pa               # об. доли (ф. 12)
    # ф. 11: пары, выходящие при открытии аппарата на загрузку, кг/цикл
    Gp = ins["Vpvp"] * phi_s / (t + 273.0) * (Pp_pa - P0_pa) * v["M"] / 8314.31
    Vt = 22.4135 * (1 + 0.00367 * t)
    rho_p = v["M"] / Vt
    Vvok = Gp * 100.0 / (rho_p * v["lel"])         # ф. 14, м³
    # ф. 5, 6: утечки через сальник мешалки/уплотнения, табл. 4.4
    f = math.pi * (mx["d_mm"] / 1000) ** 2 / 4
    Vcomm = ins["Vpvp"] + (mx["L_in"] + mx["L_out"]) * f
    Cc = 0.166 if 98.1 <= ins["Pp"] < 588.6 else None
    K = 1.5
    Ip = K * Cc * Vcomm * math.sqrt(v["M"] / (t + 273.0))
    phi_star = 3600.0 * Ip / (Vsv * mx["A"])       # кг/м³ (ф. 8, m = Iр·τ)
    phi_vol = phi_star * Vt / v["M"]               # об. доли (ф. 9)
    return dict(Vroom=Vroom, Vsv=Vsv, phi_s=phi_s, Gp=Gp, rho_p=rho_p, Vvok=Vvok,
                Vlim=0.5 * Vsv, local_load=(Vvok < 0.5 * Vsv),
                Vcomm=Vcomm, Cc=Cc, K=K, Ip=Ip, phi_star=phi_star,
                phi_vol_pct=100 * phi_vol, half_lel=0.5 * v["lel"],
                local_leak=(100 * phi_vol < 0.5 * v["lel"]),
                breather=(t >= ins["tn"]))


# ------------------------------------------- раздел 7: полное разрушение ----
def accident():
    """Расчётная авария: полное разрушение смесителя (прил. 9, 7) и ΔP (СП 12.13130).
    Расчёт ведётся по наиболее опасному веществу — его доля в разлившейся жидкости."""
    R, mx, T = INPUT["room"], INPUT["mixer"], INPUT["t_air_max"]
    h = INPUT["hazard"]
    ch = COMP[h]
    mix = mixture()
    Vsv = 0.8 * R["a"] * R["b"] * R["h"]
    Fp = R["a"] * R["b"]
    tau_off = 300.0 if mx["shutdown"] == "manual" else 120.0
    f = math.pi * (mx["d_mm"] / 1000.0) ** 2 / 4.0
    V_app = mx["V"] * mx["eps"]
    V_pump = mx["q_lps"] / 1000.0 * tau_off
    V_pipe = (mx["L_in"] + mx["L_out"]) * f
    V_liq = V_app + V_pump + V_pipe                      # растворитель Р-4, м³
    rho = mix["rho"]
    m_liq = V_liq * rho                                  # ф. 9.9
    phi_v = mix["vol"][h]                                # объёмная доля наиболее опасного вещества
    V_h = V_liq * phi_v
    m_h = V_h * ch["rho"]                                # масса наиболее опасного вещества
    fr = 1.0                                             # м²/л (растворителя > 70 %)
    Fr = fr * V_liq * 1000.0
    Fi = min(Fr, Fp)                                     # ф. 9.11
    et = eta(mx["u"], T)
    Pn = p_sat(ch, T)                                    # кПа
    W = 1e-6 * et * math.sqrt(ch["M"]) * Pn              # ф. 7.1, кг/(с·м²)
    tau_full = m_h / (W * Fi)                            # ф. 9.10
    tau = min(3600.0, tau_full)
    m = min(W * Fi * tau, m_h)                           # ф. 16
    comp = {h: dict(Pn=Pn, W=W, m=m)}
    y = {h: 1.0}
    M = ch["M"]
    Vt = 22.4135 * (1 + 0.00367 * T)                     # ф. 18
    rho_p = M / Vt
    lel = ch["lel"]
    lel_kg = M * (lel / 100.0) / Vt                      # ф. 9.13, кг/м³
    Vvok = m / lel_kg * 2.0                              # ф. 9.12, Kб = 2
    Cavg = 100.0 * m / (rho_p * Vsv)                     # ф. 19, %
    q = m / (rho_p * tau)
    a_v = mx["A"] * Vsv / 3600.0
    phi_n = lel / 100.0
    tg0 = Vsv / q * math.log(1.0 / (1.0 - phi_n))
    tg1 = Vsv / (a_v + q) * math.log(q / (q - (a_v + q) * phi_n))
    c_steady = 100.0 * q / (a_v + q)
    beta, Cst = stoich(mix, y)
    Pmax, P0, Kn, Z = 900.0, 101.0, 3.0, 0.3
    dP = (Pmax - P0) * m * Z / (Vsv * rho_p) * 100.0 / Cst / Kn
    m_crit = 5.0 * m / dP                                # масса паров, при которой ΔP = 5 кПа
    Qn = ch["Qn"]
    return dict(Vsv=Vsv, Fp=Fp, tau_off=tau_off, f=f, V_app=V_app, V_pump=V_pump,
                V_pipe=V_pipe, V_liq=V_liq, rho=rho, m_liq=m_liq, phi_v=phi_v, V_h=V_h, m_h=m_h,
                Fr=Fr, Fi=Fi, eta=et, Pn=Pn, W=W, comp=comp, W_sum=W, tau_full=tau_full, tau=tau, m=m,
                y=y, M=M, Vt=Vt, rho_p=rho_p, lel=lel, uel=ch["uel"], lel_kg=lel_kg, Vvok=Vvok,
                Vvok_lim=0.5 * Vsv, Cavg=Cavg, q=q, a_v=a_v, tg0=tg0, tg1=tg1,
                c_steady=c_steady, beta=beta, Cst=Cst, Pmax=Pmax, P0=P0, Kn=Kn, Z=Z,
                dP=dP, m_crit=m_crit, Qn=Qn,
                applic_lhs=Cavg, applic_rhs=0.5 * lel,
                applic=(Cavg < 0.5 * lel),
                category="А" if dP > 5.0 else "не А")


# ------------------------------------------------ раздел 9.3 (А): слив ------
def emergency_drain():
    """Аварийный слив самотёком из вертикального цилиндрического аппарата (прил. 14)."""
    mx = INPUT["mixer"]
    ratio = 1.5                                       # H/D корпуса — принято
    V = mx["V"]
    D = (4 * V / (math.pi * ratio)) ** (1 / 3)
    H = ratio * D
    F = math.pi * D ** 2 / 4
    H1 = mx["eps"] * H                                # начальный уровень
    H2 = 0.05                                         # остаточный уровень, м (принято)
    d = mx["d_mm"] / 1000.0
    f = math.pi * d ** 2 / 4
    mu = 0.6
    g = 9.81
    t_opor = 2 * F / (mu * f * math.sqrt(2 * g)) * (math.sqrt(H1) - math.sqrt(H2))   # ф. 14.3
    q_max = mu * f * math.sqrt(2 * g * H1)
    q_min = mu * f * math.sqrt(2 * g * H2)
    q_avg = 0.5 * (q_max + q_min)
    Vzh = V * mx["eps"]
    t_opor_b = Vzh / q_avg                            # ф. 14.4
    t_op = 60.0                                       # операции по приведению в действие, с (принято)
    t_av = t_opor + t_op
    t_av_reg = 15 * 60.0
    return dict(ratio=ratio, D=D, H=H, F=F, H1=H1, H2=H2, d=d, f=f, mu=mu,
                t_opor=t_opor, q_max=q_max, q_min=q_min, q_avg=q_avg, Vzh=Vzh,
                t_opor_b=t_opor_b, t_op=t_op, t_av=t_av, t_av_reg=t_av_reg,
                ok=(t_av <= t_av_reg), V_tank=1.0)


# ------------------------------------- раздел 9.3 (Б): огнепреградитель -----
def flame_arrester():
    """Критический диаметр канала огнепреградителя дыхательной трубы аварийной ёмкости (прил. 13)."""
    Mg, Mair = COMP["acetone"]["M"], 28.97
    vn, lam_g, Cp_g = 0.44, 0.190, 2160.0             # табл. 13.3 (ацетон)
    lam_air, Cp_air = 0.0259, 1005.0                  # воздух 20 °C
    beta = COMP["acetone"]["nC"] + COMP["acetone"]["nH"] / 4 - COMP["acetone"]["nO"] / 2
    n_o2 = beta
    n_tot = 1 + n_o2 + n_o2 * 3.76
    phi = 1.0 / n_tot                                 # стехиометрическая смесь
    R = 8314.31 / (phi * Mg + (1 - phi) * Mair)       # ф. 13.2
    lam = phi * lam_g + (1 - phi) * lam_air           # ф. 13.3
    Cp = phi * Cp_g + (1 - phi) * Cp_air              # ф. 13.4
    t = INPUT["mixer"]["t_tech"]
    Pp = INPUT["P0"] * 1000.0
    d = 65.0 * R * (t + 273.0) * lam / (vn * Cp * Pp)      # ф. 13.1, м
    d_tab = 2.45e-3                                   # табл. 13.4, ацетон
    d_use = min(d, d_tab)
    return dict(phi=phi, R=R, lam=lam, Cp=Cp, d=d, d_tab=d_tab, d_use=d_use,
                ball=3, ball_channel=2.0, layer=100 * 2.0, body=20 * 3)


def run():
    return dict(inp=INPUT, mix=mixture(), comp_limits=component_limits(),
                inside=inside(), outside=outside(), acc=accident(),
                drain=emergency_drain(), arrester=flame_arrester())


if __name__ == "__main__":
    import pprint
    pprint.pprint(run(), width=110, sort_dicts=False)
