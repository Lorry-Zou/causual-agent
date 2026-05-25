"""Test data generator for insurance AI system.
Generates 11 CSV tables across 3 business scenarios:
  1. Policy full lifecycle automated management
  2. Coverage gap diagnosis engine
  3. Intelligent consultation & conversation

Total: ~187,000 rows across 11 tables. Fixed seed for reproducibility.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
np.random.seed(SEED)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "test_data"
N_CUSTOMERS = 5000
N_POLICIES = 10000
N_EVENTS = 50000
N_PAYMENTS = 50000
N_CONV_SESSIONS = 3000

DATE_MIN = datetime.date(2022, 1, 1)
DATE_MAX = datetime.date(2026, 5, 24)
TODAY = DATE_MAX

# Chinese name components
SURNAMES = ["王","李","张","刘","陈","杨","黄","赵","吴","周","徐","孙","马","朱","胡","郭","何","高","林","罗","郑","梁","谢","宋","唐","韩","曹","许","邓","冯","萧","程","蔡","彭","潘","袁","于","董","余","苏","叶","吕","魏","蒋","田","杜","丁","沈","姜","范","江","傅","钟","卢","汪","戴","崔","任","陆","廖","姚","方","金","邱","夏","谭","韦","贾","邹","石","熊","孟","秦","阎","薛","侯","雷","白","龙","段","郝","孔","邵","史","毛","常","万","顾","赖","武","康","贺","严","尹","钱","施","牛","洪","龚"]
GIVEN_NAMES_M = ["伟","强","磊","军","勇","杰","涛","明","辉","鹏","浩","亮","刚","华","飞","超","波","健","平","林","峰","志","文","宁","云","斌","剑","毅","翔","宇","瑞","恒","晨","博","毅","恒","铭","哲","瀚","泽","楷","瑞","轩","晨","宇","辰","逸","然","景","皓","昊","睿","彦","信","哲","思","远"]
GIVEN_NAMES_F = ["芳","敏","静","丽","婷","雪","艳","娟","霞","秀英","红","玲","萍","莉","娜","燕","洁","兰","凤","梅","慧","琴","云","芬","莉","蕾","怡","欣","雅","诗","佳","雨","梦","晓","婉","若","萱","琪","瑶","月","宁","欢","颖","文","艺","丹","彤"]

PRODUCT_TYPES = {
    "YL-MM-01": "医疗险", "ZJ-CA-02": "重疾险", "YW-YL-03": "意外险",
    "SX-DS-04": "寿险", "NJ-XX-05": "年金险", "ZC-JC-06": "家财险",
    "LX-DY-07": "旅行险", "ET-ZX-08": "少儿险", "LN-ZH-09": "老人专项险",
}
PRODUCT_LIST = list(PRODUCT_TYPES.items())  # (code, name) pairs

CHANNELS = ["代理人", "银保渠道", "线上直销", "经代渠道", "电话销售", "企业团险"]
CHANNEL_WEIGHTS = [0.35, 0.15, 0.25, 0.10, 0.08, 0.07]

REGIONS = ["华北", "华东", "华南", "华中", "西南", "西北", "东北"]
REGION_PROVINCES = {
    "华北": ["北京","天津","河北","山西","内蒙古"],
    "华东": ["上海","江苏","浙江","安徽","福建","江西","山东"],
    "华南": ["广东","广西","海南"],
    "华中": ["河南","湖北","湖南"],
    "西南": ["四川","重庆","贵州","云南","西藏"],
    "西北": ["陕西","甘肃","青海","宁夏","新疆"],
    "东北": ["辽宁","吉林","黑龙江"],
}
ALL_PROVINCES = [p for v in REGION_PROVINCES.values() for p in v]

CITY_TIERS = ["一线", "新一线", "二线", "三线", "四线及以下"]
CITY_TIER_WEIGHTS = [0.12, 0.18, 0.25, 0.28, 0.17]

EDUCATION = ["高中及以下", "大专", "本科", "硕士", "博士"]
EDUCATION_WEIGHTS = [0.30, 0.25, 0.32, 0.10, 0.03]

MARITAL_STATUS = ["未婚", "已婚", "离异", "丧偶"]
FAMILY_STRUCTURES = ["单身", "二人世界", "三口之家", "四口之家", "三代同堂", "空巢", "独居老人"]

OCCUPATIONS = ["企业职员","自由职业","公务员","教师","医生","工人","农民","退休","学生","个体经营","金融从业","IT技术","服务业"]
OCCUPATION_RISK = {
    "企业职员":1,"自由职业":2,"公务员":1,"教师":1,"医生":1,"工人":3,"农民":2,"退休":0,"学生":0,
    "个体经营":2,"金融从业":1,"IT技术":1,"服务业":2,
}

POLICY_STATES = ["新保", "续保", "加保", "减保", "退保", "理赔中", "满期", "失效", "复效"]
PAYMENT_FREQ = ["趸交", "年交", "月交", "季交"]
PAYMENT_FREQ_WEIGHTS = [0.05, 0.65, 0.10, 0.20]
INSURANCE_PERIODS = ["1年", "定期", "终身"]
INSURANCE_PERIOD_WEIGHTS = [0.55, 0.30, 0.15]

EVENT_TYPES_ORDERED = [
    "投保", "生效", "续保提醒", "续保完成", "加保申请", "加保完成",
    "减保申请", "减保完成", "退保申请", "退保完成", "理赔报案", "理赔结案",
    "缴费提醒", "缴费成功", "缴费失败", "宽限期预警", "失效通知",
    "复效申请", "复效完成", "满期给付", "信息批改", "保单托管更新",
    "保单体检", "流失预警", "召回触达", "生日关怀", "节日触达",
]
EVENT_ORIGINS = ["系统自动", "人工操作", "客户自助", "外部触发"]
EVENT_ORIGIN_WEIGHTS = [0.55, 0.25, 0.15, 0.05]

CONV_CHANNELS = ["企微", "小程序", "APP", "公众号", "客服热线", "网页在线客服"]
CONV_CHANNEL_WEIGHTS = [0.15, 0.25, 0.25, 0.15, 0.10, 0.10]
CONV_INTENTS = ["产品咨询", "理赔咨询", "保障检视", "保费测算", "保单变更", "退保咨询", "投诉", "续保咨询", "健康咨询", "其他"]
CONV_INTENT_WEIGHTS = [0.25, 0.20, 0.10, 0.12, 0.15, 0.05, 0.03, 0.05, 0.03, 0.02]

KNOWLEDGE_CATEGORIES = ["产品条款", "理赔流程", "保费规则", "健康告知", "投保须知", "退保规则", "常见异议", "政策法规"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TD = datetime.timedelta  # save original for _td wrapper

def _uid(prefix: str, i: int, width: int = 8) -> str:
    return f"{prefix}{i:0{width}d}"

def _rand_date(start: datetime.date, end: datetime.date) -> datetime.date:
    days = (end - start).days
    return start + _td(days=np.random.randint(0, max(days, 1)))

def _rand_datetime(start: datetime.date, end: datetime.date) -> datetime.datetime:
    d = _rand_date(start, end)
    return datetime.datetime.combine(d, datetime.time(
        np.random.randint(0, 24), np.random.randint(0, 60), np.random.randint(0, 60)))

def _log_normal(mean_log: float, sigma_log: float, size: int = 1) -> np.ndarray:
    return np.random.lognormal(mean=mean_log, sigma=sigma_log, size=size)

def _beta(a: float, b: float, size: int = 1) -> np.ndarray:
    return np.random.beta(a, b, size=size)

def _z_inflated_poisson(lam: float, zero_prob: float, size: int = 1) -> np.ndarray:
    """Zero-inflated Poisson."""
    vals = np.random.poisson(lam=lam, size=size)
    mask = np.random.random(size=size) < zero_prob
    vals[mask] = 0
    return vals

def _weighted_choice(options: list, weights: list[float], size: int = 1) -> np.ndarray:
    probs = np.array(weights) / sum(weights)
    indices = np.random.choice(len(options), size=size, p=probs)
    if size == 1:
        return options[indices[0]]
    return np.array(options)[indices]

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))

def _safe_date(year: int, month: int, day: int) -> datetime.date:
    """Create a date safely, clamping day to month's max."""
    day = min(day, 28)  # simplest: cap at 28 to avoid all month-length issues
    return datetime.date(year, month, day)

def _td(days: int = 0, hours: int = 0, seconds: int = 0) -> datetime.timedelta:
    """Safe timedelta that casts numpy ints."""
    return _TD(days=int(days), hours=int(hours), seconds=int(seconds))

def _chinese_name(gender: str) -> str:
    surname = np.random.choice(SURNAMES)
    pool = GIVEN_NAMES_M if gender == "男" else GIVEN_NAMES_F
    given = "".join(np.random.choice(pool, size=np.random.choice([1, 2])))
    return surname + given

# ---------------------------------------------------------------------------
# Phase 1: 客户画像表
# ---------------------------------------------------------------------------

def generate_customer_profiles(n: int = N_CUSTOMERS) -> pd.DataFrame:
    print("Phase 1: 客户画像表 ...")
    rng = np.random.default_rng(SEED)

    cust_ids = [_uid("CUST", i + 1) for i in range(n)]

    # -- demographics --
    genders = rng.choice(["男", "女"], size=n, p=[0.48, 0.52])
    # Age: mixture — mostly 25-60, some children, some elderly
    age_means = rng.choice([5, 30, 42, 55, 72], size=n, p=[0.04, 0.22, 0.40, 0.24, 0.10])
    age_sigmas = rng.choice([2, 5, 6, 6, 8], size=n, p=[0.04, 0.22, 0.40, 0.24, 0.10])
    ages = np.clip(rng.normal(age_means, age_sigmas).astype(int), 0, 90)

    birth_dates = [TODAY - _td(days=int(int(a) * 365 + int(rng.integers(0, 364)))) for a in ages]

    age_bands = []
    for a in ages:
        if a <= 17: age_bands.append("少儿")
        elif a <= 25: age_bands.append("青年")
        elif a <= 35: age_bands.append("青壮")
        elif a <= 45: age_bands.append("中青")
        elif a <= 55: age_bands.append("中年")
        elif a <= 65: age_bands.append("中老")
        else: age_bands.append("老年")

    # Marital & family
    marital = []
    family = []
    children_counts = []
    has_elderly = []
    for a in ages:
        if a < 22:
            marital.append("未婚")
            family.append("单身")
            children_counts.append(0)
            has_elderly.append(0)
        elif a < 28:
            m = rng.choice(["未婚", "已婚"], p=[0.7, 0.3])
            marital.append(m)
            family.append("二人世界" if m == "已婚" else "单身")
            children_counts.append(0)
            has_elderly.append(0)
        elif a < 50:
            m = rng.choice(["已婚", "未婚", "离异"], p=[0.78, 0.14, 0.08])
            marital.append(m)
            cc = rng.poisson(1.0)
            cc = min(cc, 4)
            children_counts.append(cc)
            has_elderly.append(rng.choice([0, 1], p=[0.65, 0.35]))
            if cc == 0:
                family.append(rng.choice(["单身", "二人世界", "三代同堂"], p=[0.3, 0.6, 0.1]))
            elif cc == 1:
                family.append(rng.choice(["三口之家", "三代同堂"], p=[0.75, 0.25]))
            elif cc == 2:
                family.append(rng.choice(["四口之家", "三代同堂"], p=[0.7, 0.3]))
            else:
                family.append("三代同堂")
        elif a < 65:
            m = rng.choice(["已婚", "离异", "丧偶", "未婚"], p=[0.70, 0.12, 0.08, 0.10])
            marital.append(m)
            cc = max(0, int(rng.poisson(1.5)) - 1)  # kids likely grown
            children_counts.append(min(cc, 4))
            has_elderly.append(rng.choice([0, 1], p=[0.55, 0.45]))
            fs_choices = ["二人世界", "空巢", "三口之家", "三代同堂", "单身"]
            fs_weights = [0.40, 0.25, 0.15, 0.10, 0.10]
            family.append(rng.choice(fs_choices, p=fs_weights))
        else:
            m = rng.choice(["已婚", "丧偶", "离异", "未婚"], p=[0.50, 0.28, 0.10, 0.12])
            marital.append(m)
            children_counts.append(max(0, int(rng.poisson(2.0)) - 1))
            has_elderly.append(rng.choice([0, 1], p=[0.80, 0.20]))
            fs_choices = ["空巢", "二人世界", "独居老人", "三代同堂", "单身"]
            fs_weights = [0.35, 0.25, 0.20, 0.10, 0.10]
            family.append(rng.choice(fs_choices, p=fs_weights))

    education = _weighted_choice(EDUCATION, EDUCATION_WEIGHTS, n)
    occupations = rng.choice(OCCUPATIONS, size=n)
    occ_risk = [OCCUPATION_RISK.get(o, 2) for o in occupations]

    # Income: log-normal, correlated with education and city tier (assigned next)
    city_tiers = _weighted_choice(CITY_TIERS, CITY_TIER_WEIGHTS, n)
    provinces = rng.choice(ALL_PROVINCES, size=n)
    # map province to region
    prov_to_region = {p: r for r, plist in REGION_PROVINCES.items() for p in plist}
    regions_assigned = [prov_to_region.get(p, "华东") for p in provinces]

    # Income base by city tier
    tier_mult = {"一线": 1.8, "新一线": 1.3, "二线": 1.0, "三线": 0.7, "四线及以下": 0.5}
    edu_mult = {"高中及以下": 0.6, "大专": 0.85, "本科": 1.0, "硕士": 1.5, "博士": 2.0}
    income_base = np.array([tier_mult.get(t, 1.0) * edu_mult.get(e, 1.0) for t, e in zip(city_tiers, education)])
    incomes = _log_normal(11.0, 0.7, n) * income_base
    # Edge cases: 30 customers with 0 income
    zero_income_idx = rng.choice(n, size=30, replace=False)
    incomes[zero_income_idx] = 0

    income_bands = []
    for inc in incomes:
        if inc < 50000: income_bands.append("<5万")
        elif inc < 100000: income_bands.append("5-10万")
        elif inc < 200000: income_bands.append("10-20万")
        elif inc < 500000: income_bands.append("20-50万")
        elif inc < 1000000: income_bands.append("50-100万")
        else: income_bands.append(">100万")

    # Acquisition
    acq_channels = _weighted_choice(
        ["自然流量","转介绍","广告投放","活动获客","企业合作","代理人拓展"],
        [0.25, 0.20, 0.18, 0.15, 0.12, 0.10], n)
    acq_dates = [_rand_date(datetime.date(2018, 1, 1), DATE_MAX) for _ in range(n)]

    # Behavioral — will update policy_count after Phase 2, placeholder 0 for now
    engagement_raw = _beta(2, 3, n) * 100  # 0-100 engagement score
    complaint_counts = _z_inflated_poisson(0.3, 0.75, n).astype(int)

    # Risk level
    risk_levels = []
    for i in range(n):
        score = occ_risk[i] * 15 + (ages[i] > 55) * 20 + (complaint_counts[i] > 2) * 15 + rng.integers(0, 25)
        if score < 25: risk_levels.append("低风险")
        elif score < 40: risk_levels.append("中低风险")
        elif score < 55: risk_levels.append("中风险")
        elif score < 70: risk_levels.append("中高风险")
        else: risk_levels.append("高风险")

    # Engagement tier
    eng_tiers = []
    for s in engagement_raw:
        if s >= 80: eng_tiers.append("高度活跃")
        elif s >= 55: eng_tiers.append("活跃")
        elif s >= 30: eng_tiers.append("一般")
        elif s >= 10: eng_tiers.append("沉睡")
        else: eng_tiers.append("流失")

    interaction_freq = np.random.poisson(6.0, n)
    interaction_freq = np.where(np.array(eng_tiers) == "流失", np.random.poisson(0.5, n), interaction_freq)
    interaction_freq = np.where(np.array(eng_tiers) == "高度活跃", np.random.poisson(25, n), interaction_freq)

    # Total claims (placeholder, will refine after Phase 2)
    lifetime_claims = _z_inflated_poisson(0.5, 0.6, n).astype(int)

    df = pd.DataFrame({
        "客户ID": cust_ids,
        "姓名": [_chinese_name(g) for g in genders],
        "性别": genders,
        "出生日期": birth_dates,
        "年龄": ages,
        "年龄段": age_bands,
        "婚姻状况": marital,
        "家庭结构": family,
        "子女数量": children_counts,
        "是否有老人": has_elderly,
        "教育程度": education,
        "职业类别": occ_risk,
        "职业": occupations,
        "年收入": incomes.round(2),
        "收入段": income_bands,
        "所在省份": provinces,
        "所在城市等级": city_tiers,
        "所在区域": regions_assigned,
        "获客渠道": acq_channels,
        "获客日期": acq_dates,
        "持有保单数": 0,  # placeholder, updated after Phase 2
        "总年缴保费": 0.0,  # placeholder
        "客户价值等级": "",  # placeholder
        "风险等级": risk_levels,
        "互动频次": interaction_freq,
        "活跃度等级": eng_tiers,
        "互动评分": engagement_raw.round(2),
        "续保倾向评分": 0.0,  # placeholder
        "增购倾向评分": 0.0,  # placeholder
        "投诉次数": complaint_counts,
        "理赔次数总计": lifetime_claims,
    })

    # Edge cases: 50 customers with 0 policies (set later), 20 age 80+, 15 age 0-2
    # Already handled via age distribution
    # 25 high-complaint
    high_comp_idx = rng.choice(n, size=25, replace=False)
    df.loc[high_comp_idx, "投诉次数"] = rng.integers(5, 11, size=25)

    return df


# ---------------------------------------------------------------------------
# Phase 2: 保单主表
# ---------------------------------------------------------------------------

def generate_policy_master(cust_df: pd.DataFrame, n_pol: int = N_POLICIES) -> pd.DataFrame:
    print("Phase 2: 保单主表 ...")
    rng = np.random.default_rng(SEED)

    cust_ids = cust_df["客户ID"].tolist()
    cust_ages = dict(zip(cust_ids, cust_df["年龄"]))
    cust_children = dict(zip(cust_ids, cust_df["子女数量"]))
    cust_income = dict(zip(cust_ids, cust_df["年收入"]))
    cust_region = dict(zip(cust_ids, cust_df["所在区域"]))

    # Assign policies to customers — Poisson distribution
    policy_counts = np.clip(rng.poisson(2.0, size=len(cust_ids)), 0, 15)
    # Edge: 50 customers with 0 policies
    zero_idx = rng.choice(len(cust_ids), size=50, replace=False)
    policy_counts[zero_idx] = 0

    # Expand to per-policy records
    all_cust = []
    for cid, cnt in zip(cust_ids, policy_counts):
        all_cust.extend([cid] * cnt)
    n_actual = len(all_cust)
    # Trim or pad to exactly n_pol
    if n_actual < n_pol:
        extra = rng.choice(cust_ids, size=n_pol - n_actual)
        all_cust.extend(extra)
    else:
        all_cust = all_cust[:n_pol]
    n_actual = len(all_cust)
    rng.shuffle(all_cust[:])

    pol_ids = [_uid("POL", i + 1, 10) for i in range(n_actual)]

    # Product assignment based on customer demographics
    products = []
    for cid in all_cust:
        age = cust_ages[cid]
        has_kids = cust_children.get(cid, 0) > 0
        choices = PRODUCT_LIST.copy()
        if age < 18:
            w = [0.05, 0.05, 0.05, 0.0, 0.0, 0.0, 0.05, 0.75, 0.05]
        elif age < 25:
            w = [0.25, 0.10, 0.25, 0.05, 0.0, 0.05, 0.20, 0.05, 0.05]
        elif age < 35:
            w = [0.25, 0.20, 0.15, 0.10, 0.05, 0.10, 0.10, 0.05 if has_kids else 0.0, 0.0]
        elif age < 45:
            w = [0.20, 0.25, 0.10, 0.15, 0.10, 0.10, 0.05, 0.05 if has_kids else 0.0, 0.0]
        elif age < 55:
            w = [0.20, 0.25, 0.10, 0.15, 0.15, 0.05, 0.05, 0.0, 0.05]
        elif age < 65:
            w = [0.25, 0.15, 0.10, 0.10, 0.20, 0.05, 0.05, 0.0, 0.10]
        else:
            w = [0.25, 0.10, 0.10, 0.05, 0.10, 0.05, 0.0, 0.0, 0.35]
        w = np.array(w) / sum(w)
        idx = rng.choice(len(choices), p=w)
        products.append(choices[idx])

    product_codes = [p[0] for p in products]
    product_names = [p[1] for p in products]

    # Sum insured: log-normal with product-specific means
    product_si_mean = {
        "医疗险": 12.0, "重疾险": 12.5, "意外险": 12.0, "寿险": 13.0,
        "年金险": 12.0, "家财险": 11.5, "旅行险": 11.0, "少儿险": 11.5, "老人专项险": 11.5,
    }
    product_si_sigma = {
        "医疗险": 1.0, "重疾险": 0.8, "意外险": 0.9, "寿险": 1.2,
        "年金险": 1.0, "家财险": 0.8, "旅行险": 0.6, "少儿险": 0.8, "老人专项险": 0.7,
    }
    si_vals = np.array([
        rng.lognormal(product_si_mean[pn], product_si_sigma[pn])
        for pn in product_names
    ])
    si_vals = np.clip(si_vals, 5000, 8000000)
    # Edge: 10 policies with 0 sum insured
    si_vals[rng.choice(n_actual, size=10, replace=False)] = 0

    # Premium correlated with sum insured (r ~0.75)
    log_si = np.log(np.where(si_vals > 0, si_vals, 10000))
    prem_log = 7.0 + 0.75 * (log_si - 11.5) / 1.5 * 1.2 + rng.normal(0, 0.4, n_actual)
    premiums = np.exp(np.clip(prem_log, 4.6, 13.1))  # ~100 to ~500k
    premiums = np.where(si_vals == 0, 0, premiums)

    # Policy dates
    inception_dates = [_rand_date(datetime.date(2022, 1, 1), DATE_MAX) for _ in range(n_actual)]
    effective_dates = [d + _td(days=int(rng.integers(0, 90))) for d in inception_dates]

    # Payment
    pay_freqs = _weighted_choice(PAYMENT_FREQ, PAYMENT_FREQ_WEIGHTS, n_actual)
    pay_periods = rng.choice([1, 3, 5, 10, 15, 20, 30], size=n_actual)
    ins_periods = _weighted_choice(INSURANCE_PERIODS, INSURANCE_PERIOD_WEIGHTS, n_actual)
    # Expiry
    expiry_dates = []
    for ed, ip in zip(effective_dates, ins_periods):
        if ip == "1年":
            expiry_dates.append(ed + _td(days=365))
        elif ip == "定期":
            expiry_dates.append(ed + _td(days=365 * rng.choice([10, 15, 20, 30])))
        else:
            expiry_dates.append(ed + _td(days=365 * rng.choice([20, 30])))
    expiry_dates = [min(d, datetime.date(2060, 12, 31)) for d in expiry_dates]
    # Edge: 50 policies at exact expiry today
    for i in rng.choice(n_actual, size=50, replace=False):
        expiry_dates[i] = TODAY

    channels = _weighted_choice(CHANNELS, CHANNEL_WEIGHTS, n_actual)
    regions_assigned = [cust_region.get(cid, "华东") for cid in all_cust]

    # Auto-renewal
    auto_renew = rng.choice([0, 1], size=n_actual, p=[0.35, 0.65])

    # Renewal count (Poisson, limited by policy age)
    renewal_counts = []
    for i in range(n_actual):
        pol_age_years = max(0, (TODAY - inception_dates[i]).days / 365)
        max_renewals = int(pol_age_years)
        rc = min(rng.poisson(1.8), max_renewals, 15)
        renewal_counts.append(max(0, rc))

    # Claims
    claim_lambda = {
        "医疗险": 1.5, "重疾险": 0.3, "意外险": 0.5, "寿险": 0.15,
        "年金险": 0.05, "家财险": 0.2, "旅行险": 0.3, "少儿险": 0.6, "老人专项险": 0.8,
    }
    claim_counts = np.array([
        rng.poisson(claim_lambda.get(pn, 0.3)) for pn in product_names
    ])
    has_claim = (claim_counts > 0).astype(int)

    # Claim amounts
    claim_amounts = np.zeros(n_actual)
    for i in range(n_actual):
        if claim_counts[i] > 0:
            per_claim = rng.lognormal(np.log(max(si_vals[i], 10000)) - 2.0, 1.0, size=claim_counts[i])
            claim_amounts[i] = np.sum(np.clip(per_claim, 0, si_vals[i] * 1.5))

    # Policy state
    pol_states = []
    surrender_amounts = np.zeros(n_actual)
    surrender_dates = [None] * n_actual
    for i in range(n_actual):
        age_days = (TODAY - inception_dates[i]).days
        if age_days < 30:
            pol_states.append("新保")
        elif expiry_dates[i] <= TODAY and expiry_dates[i] >= TODAY - _td(days=30):
            pol_states.append("满期")
        elif rng.random() < 0.08 and age_days > 180:
            pol_states.append("退保")
            surrender_amounts[i] = premiums[i] * rng.uniform(0.1, 1.2)
            surrender_dates[i] = _rand_date(inception_dates[i] + _td(days=180), TODAY)
        elif rng.random() < 0.04 and age_days > 365:
            pol_states.append("失效")
        elif rng.random() < 0.03:
            pol_states.append("理赔中")
        elif rng.random() < 0.02 and age_days > 365:
            pol_states.append("复效")
        elif renewal_counts[i] > 0:
            pol_states.append(rng.choice(["续保", "加保", "减保"], p=[0.80, 0.12, 0.08]))
        else:
            pol_states.append("新保")

    # Edge: 200 policies created in the last 30 days
    for i in rng.choice(n_actual, size=min(200, n_actual), replace=False):
        inception_dates[i] = _rand_date(TODAY - _td(days=30), TODAY)
        pol_states[i] = "新保"

    df = pd.DataFrame({
        "保单ID": pol_ids,
        "客户ID": all_cust,
        "产品编码": product_codes,
        "产品类型": product_names,
        "保单状态": pol_states,
        "投保日期": inception_dates,
        "生效日期": effective_dates,
        "到期日期": expiry_dates,
        "缴费方式": pay_freqs,
        "缴费期间": pay_periods,
        "保险期间": ins_periods,
        "年缴保费": premiums.round(2),
        "保额": si_vals.round(2),
        "销售渠道": channels,
        "销售地区": regions_assigned,
        "是否自动续保": auto_renew,
        "续保次数": renewal_counts,
        "是否有理赔": has_claim,
        "累计理赔次数": claim_counts,
        "累计理赔金额": claim_amounts.round(2),
        "退保金额": surrender_amounts.round(2),
        "退保日期": surrender_dates,
    })

    # Update customer profile placeholders
    # 持有保单数
    pol_counts = df.groupby("客户ID").size()
    for cid in cust_ids:
        cust_df.loc[cust_df["客户ID"] == cid, "持有保单数"] = int(pol_counts.get(cid, 0))

    # 总年缴保费
    total_prem = df.groupby("客户ID")["年缴保费"].sum()
    for cid in cust_ids:
        cust_df.loc[cust_df["客户ID"] == cid, "总年缴保费"] = float(total_prem.get(cid, 0.0))

    # 客户价值等级
    total_prem_vals = cust_df["总年缴保费"].values
    income_vals = cust_df["年收入"].values
    value_score = np.log(np.maximum(total_prem_vals, 1)) * 0.5 + np.log(np.maximum(income_vals, 1)) * 0.5
    thresholds = np.percentile(value_score, [80, 50, 20])
    value_tiers = []
    for vs in value_score:
        if vs >= thresholds[0]: value_tiers.append("高净值")
        elif vs >= thresholds[1]: value_tiers.append("核心")
        elif vs >= thresholds[2]: value_tiers.append("大众")
        else: value_tiers.append("低价值")
    cust_df["客户价值等级"] = value_tiers

    # 续保倾向评分
    eng_map = {"高度活跃": 4, "活跃": 3, "一般": 2, "沉睡": 1, "流失": 0}
    eng_num = np.array([eng_map.get(t, 2) for t in cust_df["活跃度等级"]])
    pol_num = cust_df["持有保单数"].values
    n_cust = len(cust_df)
    renewal_prop = _sigmoid(-0.5 + eng_num * 0.4 + np.log(np.maximum(pol_num, 1)) * 0.3 + rng.normal(0, 0.3, n_cust))
    cust_df["续保倾向评分"] = renewal_prop.round(4)

    # 增购倾向评分
    cross_prop = _sigmoid(-2.0 + np.log(np.maximum(pol_num, 1)) * 0.5 + np.log(np.maximum(income_vals, 1)) * 0.3 + rng.normal(0, 0.3, n_cust))
    cust_df["增购倾向评分"] = cross_prop.round(4)

    # 理赔次数总计
    claim_total = df.groupby("客户ID")["累计理赔次数"].sum()
    for cid in cust_ids:
        cust_df.loc[cust_df["客户ID"] == cid, "理赔次数总计"] = int(claim_total.get(cid, 0))

    return df


# ---------------------------------------------------------------------------
# Phase 3: 生命周期事件日志
# ---------------------------------------------------------------------------

def generate_lifecycle_events(pol_df: pd.DataFrame, cust_df: pd.DataFrame,
                               n_events: int = N_EVENTS) -> pd.DataFrame:
    print("Phase 3: 生命周期事件日志 ...")
    rng = np.random.default_rng(SEED)

    events = []
    evt_counter = 0
    cust_ages = dict(zip(cust_df["客户ID"], cust_df["年龄"]))
    auto_renew_map = dict(zip(pol_df["保单ID"], pol_df["是否自动续保"]))
    pay_freq_map = dict(zip(pol_df["保单ID"], pol_df["缴费方式"]))

    for _, pol in pol_df.iterrows():
        pid = pol["保单ID"]
        cid = pol["客户ID"]
        inception = pol["投保日期"]
        effective = pol["生效日期"]
        expiry = pol["到期日期"]
        state = pol["保单状态"]
        has_claim_flag = pol["是否有理赔"]
        claim_count = int(pol["累计理赔次数"])
        is_auto = auto_renew_map.get(pid, 0)

        # 1) 投保 event
        evt_counter += 1
        events.append(_make_event(evt_counter, pid, cid, inception, "投保", "客户自助"))

        # 2) 生效 event
        evt_counter += 1
        events.append(_make_event(evt_counter, pid, cid, effective, "生效", "系统自动"))

        # 3) Renewal events
        renew_count = int(pol["续保次数"])
        for rc in range(renew_count):
            anniv = _safe_date(inception.year + rc + 1, inception.month, inception.day)
            if anniv > TODAY:
                break
            # Reminder 30 days before
            rem_dt = anniv - _td(days=30)
            if rem_dt > effective:
                evt_counter += 1
                events.append(_make_event(evt_counter, pid, cid, rem_dt, "续保提醒", "系统自动",
                                          action="发送续保提醒短信", action_result="成功"))
            # Completion
            comp_dt = anniv + _td(days=rng.integers(0, 15))
            if comp_dt <= TODAY:
                evt_counter += 1
                events.append(_make_event(evt_counter, pid, cid, comp_dt, "续保完成", "系统自动",
                                          action="自动续保扣款" if is_auto else "生成续保链接", action_result="成功"))

        # 4) Payment events
        freq = pay_freq_map.get(pid, "年交")
        if freq == "年交":
            pay_days = [365]
        elif freq == "月交":
            pay_days = [30 * (i + 1) for i in range(12)]
        elif freq == "季交":
            pay_days = [90 * (i + 1) for i in range(4)]
        else:
            pay_days = [0]  # 趸交 — single

        for cycle in range(min(5, max(1, (TODAY - inception).days // 365 + 1))):
            for pd_offset in pay_days:
                pay_due = inception + _td(days=cycle * 365 + pd_offset)
                if pay_due > TODAY or pay_due < inception:
                    continue
                # Reminder before
                rem_dt2 = pay_due - _td(days=7)
                if rem_dt2 > inception:
                    evt_counter += 1
                    events.append(_make_event(evt_counter, pid, cid, rem_dt2, "缴费提醒", "系统自动",
                                              action="发送缴费提醒", action_result="成功"))
                # Success or failure
                if rng.random() < 0.85:
                    evt_counter += 1
                    events.append(_make_event(evt_counter, pid, cid, pay_due, "缴费成功", "系统自动",
                                              action="自动扣款", action_result="成功"))
                else:
                    evt_counter += 1
                    events.append(_make_event(evt_counter, pid, cid, pay_due, "缴费失败", "系统自动",
                                              action="自动扣款", action_result="失败",
                                              note=rng.choice(["余额不足","卡号变更","银行拒绝"])))
                    # Grace period warning
                    grace = pay_due + _td(days=30)
                    if grace <= TODAY:
                        evt_counter += 1
                        events.append(_make_event(evt_counter, pid, cid, grace, "宽限期预警", "系统自动",
                                                  action="发送宽限期提醒"))

        # 5) Claim events
        if has_claim_flag:
            for cc in range(min(claim_count, 8)):
                claim_dt = _rand_date(effective + _td(days=30), min(expiry, TODAY))
                evt_counter += 1
                events.append(_make_event(evt_counter, pid, cid, claim_dt, "理赔报案", "客户自助",
                                          note="客户在线报案"))
                settle_dt = claim_dt + _td(days=rng.integers(1, 30))
                if settle_dt <= TODAY:
                    evt_counter += 1
                    events.append(_make_event(evt_counter, pid, cid, settle_dt, "理赔结案", "系统自动",
                                              action="自动理算赔付", action_result="成功"))

        # 6) State-specific events
        if state == "退保":
            surr_dt = pol["退保日期"]
            if surr_dt and not pd.isna(surr_dt):
                if isinstance(surr_dt, str):
                    surr_dt = datetime.date.fromisoformat(surr_dt)
                app_dt = surr_dt - _td(days=rng.integers(1, 15))
                if app_dt > effective:
                    evt_counter += 1
                    events.append(_make_event(evt_counter, pid, cid, app_dt, "退保申请", "客户自助"))
                evt_counter += 1
                events.append(_make_event(evt_counter, pid, cid, surr_dt, "退保完成", "人工操作",
                                          action="退保审核通过", action_result="成功"))
        elif state == "失效":
            lapse_dt = _rand_date(effective + _td(days=365), TODAY)
            evt_counter += 1
            events.append(_make_event(evt_counter, pid, cid, lapse_dt, "失效通知", "系统自动",
                                      action="发送失效通知"))
        elif state == "复效":
            reinstate_dt = _rand_date(effective + _td(days=400), TODAY)
            evt_counter += 1
            events.append(_make_event(evt_counter, pid, cid, reinstate_dt - _td(days=5),
                                      "复效申请", "客户自助"))
            evt_counter += 1
            events.append(_make_event(evt_counter, pid, cid, reinstate_dt, "复效完成", "人工操作",
                                      action="复效审核通过", action_result="成功"))
        elif state == "满期":
            evt_counter += 1
            events.append(_make_event(evt_counter, pid, cid, expiry, "满期给付", "系统自动",
                                      action="满期金给付", action_result="成功"))

        # 7) Periodic checkups and touchpoints
        if pol["保单状态"] in ("续保", "新保", "加保"):
            # Annual checkup
            for yr in range(1, max(1, (TODAY - inception).days // 365 + 1)):
                chk_dt = _safe_date(inception.year + yr, rng.integers(1, 13), rng.integers(1, 29))
                if chk_dt > TODAY:
                    continue
                evt_counter += 1
                events.append(_make_event(evt_counter, pid, cid, chk_dt, "保单体检", "系统自动",
                                          action="自动保单检视报告"))
            # Birthday touchpoint
            c_age = cust_ages.get(cid, 35)
            bday_this_year = _safe_date(TODAY.year, rng.integers(1, 13), rng.integers(1, 29))
            if bday_this_year <= TODAY and bday_this_year >= inception:
                evt_counter += 1
                events.append(_make_event(evt_counter, pid, cid, bday_this_year, "生日关怀", "系统自动",
                                          action="发送生日祝福及专属优惠"))

    # Sort and trim
    events.sort(key=lambda e: e["事件时间"])
    events = events[:n_events]

    # Edge case: 30 policies with duplicate events (add before deriving columns)
    dup_pids = rng.choice(pol_df["保单ID"].tolist(), size=min(30, len(pol_df)), replace=False)
    for pid in dup_pids:
        pid_events = [e for e in events if e["保单ID"] == pid]
        if len(pid_events) >= 2:
            dup = pid_events[0].copy()
            dup["事件ID"] = _uid("EVT", evt_counter + 1)
            evt_counter += 1
            events.append(dup)

    n_evt = len(events)

    # Fill response times
    resp_times = []
    for e in events:
        if e["事件来源"] == "系统自动":
            resp_times.append(round(rng.lognormal(-2.0, 1.0), 2))
        elif e["事件来源"] == "人工操作":
            resp_times.append(round(rng.lognormal(1.5, 1.2), 2))
        else:
            resp_times.append(round(rng.lognormal(0.5, 1.5), 2))

    # Edge: 200 events with response > 168 hours
    for fi in rng.choice(n_evt, size=min(200, n_evt), replace=False):
        resp_times[fi] = round(rng.uniform(168, 720), 2)

    # Edge: 500 events with failed automated actions
    fail_idx = rng.choice(n_evt, size=min(500, n_evt), replace=False)
    for fi in fail_idx:
        if events[fi]["自动化动作"]:
            events[fi]["自动化动作结果"] = "失败"

    df = pd.DataFrame(events)
    df["渠道"] = _weighted_choice(
        ["企微","小程序","公众号","APP","客服热线","代理人"],
        [0.15, 0.25, 0.20, 0.25, 0.08, 0.07], n_evt)
    df["响应时间"] = resp_times
    return df


def _make_event(evt_id: int, pol_id: str, cust_id: str, dt, evt_type: str, origin: str,
                action: str = "", action_result: str = "", note: str = "") -> dict:
    """Create a single event record."""
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        dt = datetime.datetime.combine(dt, datetime.time(
            np.random.randint(0, 24), np.random.randint(0, 60), np.random.randint(0, 60)))
    return {
        "事件ID": _uid("EVT", evt_id),
        "保单ID": pol_id,
        "客户ID": cust_id,
        "事件时间": dt,
        "事件类型": evt_type,
        "事件来源": origin,
        "触发条件": "",
        "自动化动作": action,
        "自动化动作结果": action_result if action else "",
        "人工跟进标记": 0 if origin == "系统自动" else np.random.choice([0, 1], p=[0.3, 0.7]),
        "人工跟进结果": "",
        "关联理赔ID": "",
        "事件备注": note,
    }


# ---------------------------------------------------------------------------
# Phase 4: 缴费记录表
# ---------------------------------------------------------------------------

def generate_payment_records(pol_df: pd.DataFrame, n_pay: int = N_PAYMENTS) -> pd.DataFrame:
    print("Phase 4: 缴费记录表 ...")
    rng = np.random.default_rng(SEED)

    records = []
    pay_counter = 0

    for _, pol in pol_df.iterrows():
        pid = pol["保单ID"]
        cid = pol["客户ID"]
        inception = pol["投保日期"]
        freq = pol["缴费方式"]
        premium = pol["年缴保费"]
        status = pol["保单状态"]

        if freq == "年交":
            periods_per_year, interval_days = 1, 365
            per_pay = premium
        elif freq == "月交":
            periods_per_year, interval_days = 12, 30
            per_pay = premium / 12
        elif freq == "季交":
            periods_per_year, interval_days = 4, 90
            per_pay = premium / 4
        else:  # 趸交
            periods_per_year, interval_days = 1, 0
            per_pay = premium

        years_active = max(1, (TODAY - inception).days // 365 + 1)
        for year_idx in range(min(years_active, 5)):
            for period in range(periods_per_year):
                due = inception + _td(days=year_idx * 365 + period * interval_days)
                if due > TODAY or due < inception:
                    continue
                pay_counter += 1

                # Payment status
                status_roll = rng.random()
                if status_roll < 0.85:
                    pay_status = "已缴"
                    actual_dt = due + _td(days=rng.integers(-5, 10))
                    actual_amt = per_pay
                    fail_reason = ""
                elif status_roll < 0.90:
                    pay_status = "宽限期内"
                    actual_dt = None
                    actual_amt = None
                    fail_reason = ""
                elif status_roll < 0.94:
                    pay_status = "未缴"
                    actual_dt = None
                    actual_amt = None
                    fail_reason = rng.choice(["余额不足", "卡号变更", "银行拒绝"])
                elif status_roll < 0.97:
                    pay_status = "已逾期"
                    actual_dt = None
                    actual_amt = None
                    fail_reason = rng.choice(["余额不足", "卡号变更"])
                elif status_roll < 0.99:
                    pay_status = "已失效"
                    actual_dt = None
                    actual_amt = None
                    fail_reason = ""
                else:
                    pay_status = "豁免"
                    actual_dt = due
                    actual_amt = 0
                    fail_reason = "保费豁免"

                grace_end = due + _td(days=60)
                lapse_dt = due + _td(days=90) if pay_status in ("已逾期", "已失效") else None

                records.append({
                    "缴费记录ID": _uid("PAY", pay_counter),
                    "保单ID": pid,
                    "客户ID": cid,
                    "应缴日期": due,
                    "应缴金额": round(per_pay, 2),
                    "实缴日期": actual_dt,
                    "实缴金额": round(actual_amt, 2) if actual_amt else None,
                    "缴费状态": pay_status,
                    "缴费方式": rng.choice(["银行代扣","微信支付","支付宝","银行卡转账","现金","对公转账"]),
                    "扣款失败原因": fail_reason,
                    "宽限期截止日": grace_end,
                    "失效日期": lapse_dt,
                    "复效日期": None,
                    "复效补缴金额": None,
                })

        if pay_counter >= n_pay * 1.2:
            break

    df = pd.DataFrame(records)
    return df.head(n_pay)


# ---------------------------------------------------------------------------
# Phase 5: 客户保障概况表
# ---------------------------------------------------------------------------

def generate_coverage_profiles(cust_df: pd.DataFrame, pol_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 5: 客户保障概况表 ...")
    rng = np.random.default_rng(SEED)

    # Aggregate existing coverage from policies by product type
    policy_coverage = {}
    for _, pol in pol_df.iterrows():
        cid = pol["客户ID"]
        ptype = pol["产品类型"]
        si = pol["保额"]
        if cid not in policy_coverage:
            policy_coverage[cid] = {}
        policy_coverage[cid][ptype] = policy_coverage[cid].get(ptype, 0) + si

    records = []
    for i, (_, cust) in enumerate(cust_df.iterrows()):
        cid = cust["客户ID"]
        income = cust["年收入"]
        children = cust["子女数量"]
        has_elderly_flag = cust["是否有老人"]
        age = cust["年龄"]

        pc = policy_coverage.get(cid, {})

        household_income = income * rng.uniform(1.0, 2.5) if income > 0 else rng.lognormal(11.0, 0.5)
        household_expense = household_income * rng.uniform(0.3, 0.8)

        # Mortgage — 40% have none
        mort = 0 if rng.random() < 0.4 else rng.lognormal(12.0, 1.0)
        other_debt = 0 if rng.random() < 0.5 else rng.lognormal(10.0, 1.2)

        # Education reserve
        edu_reserve = 0
        if children > 0:
            edu_reserve = children * rng.lognormal(12.0, 0.8)

        # Elder care
        elder_expense = 0
        if has_elderly_flag:
            elder_expense = rng.lognormal(9.5, 0.8)

        # Public insurance
        if rng.random() < 0.45:
            shebao_type = "城镇职工医保"
            shebao_ratio = rng.beta(7, 2) * 0.4 + 0.55
            shebao_cap = rng.choice([200000, 300000, 400000, 500000])
        elif rng.random() < 0.70:
            shebao_type = "城乡居民医保"
            shebao_ratio = rng.beta(5, 3) * 0.3 + 0.40
            shebao_cap = rng.choice([100000, 150000, 200000])
        elif rng.random() < 0.90:
            shebao_type = "新农合"
            shebao_ratio = rng.beta(4, 4) * 0.2 + 0.30
            shebao_cap = rng.choice([80000, 100000, 150000])
        elif rng.random() < 0.95:
            shebao_type = "公费医疗"
            shebao_ratio = rng.beta(9, 1) * 0.15 + 0.80
            shebao_cap = 500000
        else:
            shebao_type = "无社保"
            shebao_ratio = 0
            shebao_cap = 0

        # Employer supplemental
        emp_supp = 0 if rng.random() < 0.6 else rng.lognormal(9.5, 1.0)

        # Health risk
        health_risk = rng.beta(2, 5) * 100
        # Pre-existing conditions
        conditions_pool = ["高血压", "糖尿病", "高血脂", "冠心病", "甲状腺结节", "乳腺结节", "脂肪肝", "慢性胃炎", "无"]
        n_cond = rng.poisson(1.2)
        conditions = rng.choice(conditions_pool[:-1], size=min(n_cond, 4), replace=False).tolist()
        if not conditions:
            conditions = ["无"]
        # Edge: older customers more conditions
        if age > 60 and rng.random() < 0.6:
            conditions = rng.choice(conditions_pool[:-1], size=min(rng.integers(1, 4), 4), replace=False).tolist()

        abnormal_items = rng.poisson(1.5)

        # Income protection multiplier
        income_protect = min(10, max(3, (household_expense * 10 + mort + other_debt + edu_reserve) / max(income, 1)))

        records.append({
            "客户保障ID": _uid("CPROF", i + 1),
            "客户ID": cid,
            "评估日期": _rand_date(datetime.date(2023, 1, 1), TODAY),
            "年收入": income,
            "家庭年收入": round(household_income, 2),
            "家庭年支出": round(household_expense, 2),
            "房贷余额": round(mort, 2),
            "其他负债": round(other_debt, 2),
            "子女教育储备需求": round(edu_reserve, 2),
            "赡养老人年支出": round(elder_expense, 2),
            "已有医疗险保额": round(pc.get("医疗险", 0) + rng.lognormal(10.0, 1.5) * (0.3 if pc.get("医疗险", 0) == 0 else 0.05), 2),
            "已有重疾险保额": round(pc.get("重疾险", 0) + rng.lognormal(10.5, 1.2) * (0.3 if pc.get("重疾险", 0) == 0 else 0.05), 2),
            "已有意外险保额": round(pc.get("意外险", 0) + rng.lognormal(10.5, 1.3) * (0.3 if pc.get("意外险", 0) == 0 else 0.05), 2),
            "已有寿险保额": round(pc.get("寿险", 0) + rng.lognormal(10.5, 1.5) * (0.3 if pc.get("寿险", 0) == 0 else 0.05), 2),
            "已有家财险保额": round(pc.get("家财险", 0) + rng.lognormal(9.0, 1.5) * (0.3 if pc.get("家财险", 0) == 0 else 0.05), 2),
            "社保类型": shebao_type,
            "社保报销比例": round(shebao_ratio, 4),
            "社保封顶线": shebao_cap,
            "企业补充医疗": round(emp_supp, 2),
            "健康风险评分": round(health_risk, 2),
            "既往病史标签": "|".join(conditions),
            "体检异常数": abnormal_items,
            "职业风险等级": cust["职业类别"],
            "收入保障需求倍率": round(income_protect, 2),
            "数据来源": rng.choice(["客户填报","保单数据汇总","理赔数据推算","第三方数据"]),
        })

    df = pd.DataFrame(records)
    # Edge: 100 customers with all coverage = 0
    for i in rng.choice(len(df), size=min(100, len(df)), replace=False):
        for col in ["已有医疗险保额","已有重疾险保额","已有意外险保额","已有寿险保额","已有家财险保额"]:
            df.loc[i, col] = 0
    # Edge: 50 with 无社保
    for i in rng.choice(len(df), size=min(50, len(df)), replace=False):
        df.loc[i, "社保类型"] = "无社保"
        df.loc[i, "社保报销比例"] = 0
        df.loc[i, "社保封顶线"] = 0

    return df


# ---------------------------------------------------------------------------
# Phase 6: 保障缺口诊断结果表
# ---------------------------------------------------------------------------

def generate_gap_results(cov_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 6: 保障缺口诊断结果表 ...")
    rng = np.random.default_rng(SEED)

    dimensions = [
        ("医疗报销缺口", "医疗险"),
        ("重疾保障缺口", "重疾险"),
        ("意外保障缺口", "意外险"),
        ("寿险保障缺口", "寿险"),
        ("家财保障缺口", "家财险"),
        ("养老储蓄缺口", "年金险"),
        ("子女教育缺口", "少儿险"),
    ]

    records = []
    counter = 0
    for _, cov in cov_df.iterrows():
        cid = cov["客户ID"]
        cpid = cov["客户保障ID"]
        diag_date = cov["评估日期"] + _td(days=rng.integers(1, 30))
        income = cov["年收入"]
        hh_expense = cov["家庭年支出"]
        mortgage = cov["房贷余额"]
        other_debt = cov["其他负债"]
        edu_reserve = cov["子女教育储备需求"]
        shebao_cap = cov["社保封顶线"]

        existing_map = {
            "医疗险": cov["已有医疗险保额"],
            "重疾险": cov["已有重疾险保额"],
            "意外险": cov["已有意外险保额"],
            "寿险": cov["已有寿险保额"],
            "家财险": cov["已有家财险保额"],
            "年金险": 0,  # tracked separately
            "少儿险": 0,
        }

        for dim_name, product_key in dimensions:
            counter += 1
            existing = existing_map.get(product_key, 0)

            # Ideal coverage calculation
            if dim_name == "医疗报销缺口":
                ideal = max(shebao_cap * 2, hh_expense * 5)
                ideal = max(ideal, 200000)
            elif dim_name == "重疾保障缺口":
                ideal = max(300000, income * 3)
            elif dim_name == "意外保障缺口":
                ideal = max(500000, income * 10)
            elif dim_name == "寿险保障缺口":
                ideal = max(mortgage + other_debt + hh_expense * 10, income * 5)
            elif dim_name == "家财保障缺口":
                ideal = max(mortgage * 0.5, 300000)
            elif dim_name == "养老储蓄缺口":
                ideal = hh_expense * 15
            elif dim_name == "子女教育缺口":
                ideal = edu_reserve * 1.5 if edu_reserve > 0 else 0
            else:
                ideal = 100000

            ideal = max(ideal, 50000)
            minimum = ideal * 0.5

            gap_amount = max(0, ideal - existing)
            # Gap classification
            coverage_ratio = existing / max(ideal, 1)
            if coverage_ratio < 0.2:
                gap_class = "严重不足"
            elif coverage_ratio < 0.5:
                gap_class = "不足"
            elif coverage_ratio < 0.8:
                gap_class = "基本充足"
            elif coverage_ratio < 1.2:
                gap_class = "充足"
            else:
                gap_class = "过度保障"

            # Severity score
            severity = min(100, (gap_amount / max(ideal, 1)) * 100) if gap_class != "过度保障" else rng.uniform(0, 20)
            current_level = min(100, max(0, coverage_ratio * 100))

            # Priority
            if dim_name in ("医疗报销缺口", "重疾保障缺口"):
                priority_base = 1
            elif dim_name in ("寿险保障缺口", "养老储蓄缺口"):
                priority_base = 2
            elif dim_name == "意外保障缺口":
                priority_base = 3
            else:
                priority_base = 4
            priority = min(5, priority_base + (0 if gap_class in ("充足", "过度保障") else 1))

            # Recommended product
            rec_code = ""
            rec_type = ""
            est_premium = 0.0
            if gap_amount > 0:
                for code, pname in PRODUCT_TYPES.items():
                    if pname == product_key:
                        rec_code = code
                        rec_type = pname
                        break
                if rec_type == "医疗险":
                    est_premium = rng.lognormal(np.log(ideal * 0.02), 0.5)
                elif rec_type == "重疾险":
                    est_premium = rng.lognormal(np.log(ideal * 0.03), 0.4)
                elif rec_type == "意外险":
                    est_premium = rng.lognormal(np.log(ideal * 0.005), 0.5)
                elif rec_type == "寿险":
                    est_premium = rng.lognormal(np.log(ideal * 0.015), 0.4)
                else:
                    est_premium = rng.lognormal(np.log(ideal * 0.02), 0.5)

            config = rng.choice(["极简版", "标准版", "全面版", "高端版"])

            records.append({
                "诊断结果ID": _uid("GAP", counter),
                "客户保障ID": cpid,
                "客户ID": cid,
                "诊断日期": diag_date,
                "保障维度": dim_name,
                "缺口识别结果": gap_class,
                "缺口严重度评分": round(severity, 2),
                "当前保障水平": round(current_level, 2),
                "建议最低保额": round(minimum, 2),
                "建议理想保额": round(ideal, 2),
                "保额缺口金额": round(gap_amount, 2),
                "缺口优先级": priority,
                "推荐产品编码": rec_code,
                "推荐产品类型": rec_type,
                "预估年保费": round(est_premium, 2),
                "预算适配度": round(rng.beta(5, 3), 4),
                "配置方案版本": config,
                "方案优先级": rng.integers(1, 4),
                "自动生成方案摘要": f"针对{dim_name}，当前保障{existing:,.0f}元，建议提升至{ideal:,.0f}元，缺口{gap_amount:,.0f}元。推荐配置{rec_type}{config}。",
            })

    df = pd.DataFrame(records)
    # Edge: 200 rows with negative gap (over-insured)
    over_idx = df[df["缺口识别结果"] == "过度保障"].index[:200]
    for oi in over_idx:
        df.loc[oi, "保额缺口金额"] = -abs(df.loc[oi, "保额缺口金额"])

    return df


# ---------------------------------------------------------------------------
# Phase 7: 缺口诊断日志表
# ---------------------------------------------------------------------------

def generate_gap_diagnosis_logs(cust_df: pd.DataFrame, cov_df: pd.DataFrame,
                                 gap_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 7: 缺口诊断日志表 ...")
    rng = np.random.default_rng(SEED)

    records = []
    counter = 0
    trigger_reasons = ["定期巡检","新单投保触发","客户主动查询","保单变更触发","续保前评估","理赔后评估","行为事件触发","营销活动触发"]
    trigger_weights = [0.35, 0.15, 0.12, 0.12, 0.10, 0.08, 0.05, 0.03]
    model_versions = ["gap-v2.1.0", "gap-v2.2.0", "gap-v2.3.1", "gap-v3.0.0-beta"]
    model_types = ["规则引擎", "XGBoost", "随机森林", "LLM+推理", "混合模型"]

    # Each customer gets 1-3 diagnoses over time
    for _, cov in cov_df.iterrows():
        cid = cov["客户ID"]
        n_diag = rng.integers(1, 4)
        base_date = cov["评估日期"]
        for d in range(n_diag):
            counter += 1
            diag_dt = base_date + _td(days=d * rng.integers(90, 365))
            if diag_dt > TODAY:
                diag_dt = base_date

            # Model version evolves over time
            days_from_start = (diag_dt - datetime.date(2023, 6, 1)).days
            if days_from_start < 180:
                mv = "gap-v2.1.0"
            elif days_from_start < 365:
                mv = rng.choice(["gap-v2.1.0", "gap-v2.2.0"], p=[0.3, 0.7])
            elif days_from_start < 600:
                mv = rng.choice(["gap-v2.2.0", "gap-v2.3.1"], p=[0.2, 0.8])
            else:
                mv = rng.choice(["gap-v2.3.1", "gap-v3.0.0-beta"], p=[0.4, 0.6])

            n_features = rng.integers(5, 81)
            exec_time = rng.lognormal(-0.5, 0.8) + n_features * 0.01

            conf_medical = rng.beta(8, 2)
            conf_ci = rng.beta(8, 2)
            conf_accident = rng.beta(7, 2.5)
            conf_life = rng.beta(7, 2)
            conf_overall = np.mean([conf_medical, conf_ci, conf_accident, conf_life])
            conf_pass = conf_overall >= 0.7
            manual_review = not conf_pass or rng.random() < 0.1

            records.append({
                "诊断日志ID": _uid("DLOG", counter),
                "客户ID": cid,
                "诊断运行时间": datetime.datetime.combine(diag_dt, datetime.time(rng.integers(0, 24), rng.integers(0, 60))),
                "触发原因": _weighted_choice(trigger_reasons, trigger_weights),
                "关联触发事件ID": "",
                "AI模型版本": mv,
                "模型类型": rng.choice(model_types),
                "输入特征数": n_features,
                "诊断耗时": round(exec_time, 3),
                "医疗缺口置信度": round(conf_medical, 4),
                "重疾缺口置信度": round(conf_ci, 4),
                "意外缺口置信度": round(conf_accident, 4),
                "寿险缺口置信度": round(conf_life, 4),
                "综合置信度": round(conf_overall, 4),
                "置信度是否达标": int(conf_pass),
                "是否人工复核": int(manual_review),
                "复核结果": "",
                "诊断输出摘要": json.dumps({"gap_count": int(rng.integers(2, 8)), "severe_gaps": int(rng.integers(0, 4))}, ensure_ascii=False),
                "模型输入快照JSON": "{}",
                "异常标记": int(rng.random() < 0.05),
            })

    df = pd.DataFrame(records)
    # Edge: 100 logs with exec time > 60s
    for i in rng.choice(len(df), size=min(100, len(df)), replace=False):
        df.loc[i, "诊断耗时"] = round(rng.uniform(60, 120), 3)
    # Edge: 50 logs with very low confidence
    for i in rng.choice(len(df), size=min(50, len(df)), replace=False):
        for col in ["医疗缺口置信度","重疾缺口置信度","意外缺口置信度","寿险缺口置信度"]:
            df.loc[i, col] = round(rng.beta(2, 5), 4)
        df.loc[i, "综合置信度"] = round(df.loc[i, ["医疗缺口置信度","重疾缺口置信度","意外缺口置信度","寿险缺口置信度"]].mean(), 4)

    return df


# ---------------------------------------------------------------------------
# Phase 8: 对话会话表
# ---------------------------------------------------------------------------

def generate_conversation_sessions(cust_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 8: 对话会话表 ...")
    rng = np.random.default_rng(SEED)

    cust_ids = cust_df["客户ID"].tolist()
    records = []

    for i in range(N_CONV_SESSIONS):
        # Assign customer — some anonymous
        is_anon = rng.random() < 0.03
        cid = "" if is_anon else rng.choice(cust_ids)

        start_dt = _rand_datetime(datetime.date(2024, 1, 1), DATE_MAX)
        msg_turns = max(1, rng.poisson(4.5))
        duration_sec = int(rng.lognormal(5.5, 1.2) + msg_turns * rng.uniform(80, 150))
        duration_sec = min(duration_sec, 7200)
        end_dt = start_dt + _td(seconds=max(10, duration_sec))

        channel = _weighted_choice(CONV_CHANNELS, CONV_CHANNEL_WEIGHTS)
        init_type = rng.choice(["客户主动发起", "系统主动推送", "转人工", "预约回访"], p=[0.55, 0.20, 0.15, 0.10])

        primary_intent = _weighted_choice(CONV_INTENTS, CONV_INTENT_WEIGHTS)
        secondary = "" if rng.random() < 0.7 else _weighted_choice(CONV_INTENTS, CONV_INTENT_WEIGHTS)

        intent_conf = rng.beta(9, 1)

        user_msgs = max(1, msg_turns // 2 + rng.integers(-1, 2))
        ai_msgs = msg_turns - user_msgs

        first_resp_time = rng.lognormal(1.0 if channel not in ("客服热线",) else 2.0, 1.0)
        avg_resp_time = rng.lognormal(1.5, 0.8)

        escalated = rng.random() < 0.18
        esc_reason = ""
        esc_turn = 0
        if escalated:
            esc_reason = rng.choice(["AI无法解答","客户要求","高风险投诉","复杂理赔"])
            esc_turn = int(rng.integers(1, max(2, msg_turns)))

        resolved = rng.random() < (0.75 if not escalated else 0.55)
        if resolved:
            res_status = rng.choice(["完全解决", "部分解决", "转人工后解决"], p=[0.7, 0.2, 0.1])
        else:
            res_status = rng.choice(["未解决", "客户放弃", "超时会话"], p=[0.5, 0.3, 0.2])

        csat = 0
        if rng.random() < 0.6:
            if resolved and not escalated:
                csat = rng.choice([3, 4, 5], p=[0.15, 0.40, 0.45])
            elif resolved:
                csat = rng.choice([2, 3, 4, 5], p=[0.15, 0.30, 0.35, 0.20])
            else:
                csat = rng.choice([1, 2, 3], p=[0.40, 0.35, 0.25])

        sentiment_start = rng.beta(4, 3)
        sentiment_end = sentiment_start + rng.uniform(-0.3, 0.3) * (1 if resolved else -0.5)
        sentiment_end = np.clip(sentiment_end, 0, 1)
        sentiment_score = round(sentiment_end * 2 - 1, 4)  # -1 to 1

        if sentiment_end - sentiment_start > 0.15:
            sent_trend = "正向改善"
        elif sentiment_end - sentiment_start < -0.15:
            sent_trend = "负向恶化"
        elif abs(sentiment_end - sentiment_start) < 0.05:
            sent_trend = "稳定中性"
        else:
            sent_trend = "波动剧烈"

        # Topics
        topic_pool = {
            "产品咨询": ["百万医疗","免赔额","等待期","保障范围","健康告知"],
            "理赔咨询": ["理赔流程","理赔材料","理赔时效","定点医院","赔付比例"],
            "保障检视": ["保单整理","保障缺口","家庭方案","保额测算"],
            "保费测算": ["费率","缴费方式","保费对比"],
            "保单变更": ["加保","减保","受益人变更","联系方式变更"],
            "退保咨询": ["退保流程","现金价值","退保损失","犹豫期"],
            "投诉": ["服务态度","理赔纠纷","销售误导"],
            "续保咨询": ["续保条件","保费变化","保证续保"],
            "健康咨询": ["体检异常","既往症","核保结论"],
            "其他": ["一般咨询"],
        }
        p_topics = topic_pool.get(primary_intent, ["一般咨询"])
        s_topics = topic_pool.get(secondary, []) if secondary else []
        all_topics = list(set(p_topics[:2] + s_topics[:1]))
        topic_tags = "|".join(all_topics) if all_topics else "一般咨询"

        has_recommendation = int(rng.random() < 0.25)
        rec_clicked = int(rng.random() < 0.4) if has_recommendation else 0
        compliance_flag = int(rng.random() < 0.02)

        records.append({
            "会话ID": _uid("CONV", i + 1),
            "客户ID": cid if cid else None,
            "会话开始时间": start_dt,
            "会话结束时间": end_dt,
            "会话时长": duration_sec,
            "会话渠道": channel,
            "会话发起方式": init_type,
            "主要意图": primary_intent,
            "次要意图": secondary if secondary else None,
            "意图置信度": round(intent_conf, 4),
            "实体提取结果": "{}",
            "消息轮次": msg_turns,
            "用户消息数": user_msgs,
            "AI消息数": ai_msgs,
            "首次响应时间": round(first_resp_time, 2),
            "平均响应时间": round(avg_resp_time, 2),
            "是否转人工": int(escalated),
            "转人工原因": esc_reason if esc_reason else None,
            "转人工轮次": esc_turn if esc_turn else None,
            "是否已解决": int(resolved),
            "解决状态": res_status,
            "客户满意度评分": csat if csat > 0 else None,
            "客户情绪评分": sentiment_score,
            "情绪趋势": sent_trend,
            "关键话题标签": topic_tags,
            "是否包含产品推荐": has_recommendation,
            "推荐点击率": rec_clicked,
            "会话摘要": f"客户通过{channel}咨询{primary_intent}，共{msg_turns}轮对话，{'已解决' if resolved else '未解决'}。",
            "合规标记": compliance_flag,
        })

    df = pd.DataFrame(records)
    # Edge: 50 long sessions, 80 immediate escalation, 40 CSAT=1
    long_idx = rng.choice(len(df), size=50, replace=False)
    df.loc[long_idx, "消息轮次"] = rng.integers(30, 51)
    esc_idx = rng.choice(len(df), size=80, replace=False)
    df.loc[esc_idx, "转人工轮次"] = 1
    df.loc[esc_idx, "是否转人工"] = 1
    return df


# ---------------------------------------------------------------------------
# Phase 9: 对话消息明细表
# ---------------------------------------------------------------------------

def generate_conversation_messages(sess_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 9: 对话消息明细表 ...")
    rng = np.random.default_rng(SEED)

    records = []
    msg_counter = 0

    # Templates for generating realistic messages
    user_templates = {
        "产品咨询": [
            "我想了解一下{product}的保障范围",
            "{product}的免赔额是多少？",
            "这个产品等待期多久？",
            "{product}和市场上其他产品比有什么优势？",
            "健康告知没通过怎么办？",
            "请问{product}能覆盖门诊吗？",
            "我家小孩{age}岁，能买这个产品吗？",
            "这个产品续保条件怎么样？",
        ],
        "理赔咨询": [
            "我上个月住院了，怎么申请理赔？",
            "理赔需要准备哪些材料？",
            "理赔大概多久能到账？",
            "你们定点医院有哪些？",
            "我在外地就医能报销吗？",
            "上次理赔被拒了，原因是什么？",
        ],
        "保障检视": [
            "帮我看看我目前的保障够不够",
            "我家里有老人小孩，需要怎么配置保险？",
            "我现在的保额是不是太低了？",
            "能帮我做个家庭保障方案吗？",
        ],
        "保费测算": [
            "帮我算一下{product}的保费",
            "我今年{age}岁，买百万医疗多少钱？",
            "月交和年交哪个划算？",
            "两个人一起买有没有优惠？",
        ],
        "保单变更": [
            "我想加保{product}",
            "我要变更受益人",
            "想降低保额，怎么操作？",
            "我的联系方式变了，怎么更新？",
        ],
        "退保咨询": [
            "我想退保，流程是什么？",
            "退保能退多少钱？",
            "犹豫期内退保有什么不同？",
            "退保后还能再买吗？",
        ],
        "投诉": [
            "我要投诉，理赔太慢了",
            "你们的代理人误导销售",
            "为什么扣费了但保单没生效？",
            "客服态度太差了，我要投诉",
        ],
        "续保咨询": [
            "我的保单快到期了，怎么续保？",
            "续保保费会涨吗？",
            "保证续保是什么意思？",
        ],
        "健康咨询": [
            "我有高血压能买重疾险吗？",
            "体检有结节，会影响核保吗？",
            "既往症是什么意思？",
        ],
        "其他": [
            "你好，我想咨询一下保险",
            "能帮我查一下我的保单吗？",
            "App上怎么操作理赔？",
        ],
    }
    ai_templates = {
        "产品咨询": [
            "您好！{product}保障范围包括住院医疗、特殊门诊、门诊手术等，具体以条款为准。",
            "{product}的免赔额为每年{deductible}元，社保报销部分可抵扣免赔额。",
            "这款产品的等待期为{waiting_days}天，意外伤害无等待期。",
            "我们的产品在续保条件、增值服务等方面具有明显优势，比如就医绿通、费用垫付等。",
            "如果健康告知未通过，建议您尝试智能核保功能，可能会有除外承保或加费承保的可能。",
            "这款产品{coverage}，具体可以查看产品条款中的保障责任部分。",
        ],
        "理赔咨询": [
            "理赔流程：1)在APP或公众号报案 2)上传理赔材料 3)审核 4)赔付。一般{claim_days}个工作日内到账。",
            "需要的材料包括：身份证、病历、费用清单、发票原件、银行卡信息。",
            "我们合作的定点医院覆盖全国{network_count}+家，具体可以查询APP中的医院列表。",
            "异地就医可以报销，但需要提前备案，报销比例按参保地政策执行。",
        ],
        "保障检视": [
            "根据您的家庭情况，建议配置：医疗险(基础)、重疾险(收入补偿)、意外险(身故/伤残保障)。",
            "您的重疾保额建议不低于年收入的3倍，目前建议补充。",
            "已为您生成家庭保障方案，包含极简版、标准版、全面版三个配置，请查收。",
        ],
        "保费测算": [
            "根据您的年龄{age}岁，{product}年保费约{premium}元。",
            "年交总费用比月交节省约5%，建议选择年交。",
        ],
        "保单变更": [
            "加保/减保可通过APP-保单服务-变更申请提交，{days}个工作日内处理。",
            "受益人变更需要提供新受益人身份证信息，可在APP直接操作。",
        ],
        "退保咨询": [
            "退保请通过APP或联系客服办理，犹豫期(15天)内退保全额退款。",
            "您的保单当前现金价值约{cash_value}元，退保会有一定损失，请谨慎考虑。",
        ],
        "投诉": [
            "非常抱歉给您带来不便，我已经记录您的投诉，将优先处理并在24小时内回复。",
            "您的投诉已受理，工单号{ticket_id}，会有专人跟进处理。",
        ],
        "续保咨询": [
            "续保在保单到期前30天开放，我们会通过短信和APP提醒您。",
            "保证续保期间内，不会因理赔或健康状况变化而拒绝续保。",
        ],
        "健康咨询": [
            "有既往症可能会影响核保结论，建议如实告知后进行智能核保评估。",
            "部分结节在稳定期后可以标准体承保，具体需要看检查报告。",
        ],
        "其他": [
            "您好，我是AI保险顾问，请问有什么可以帮您？",
            "正在为您查询，请稍候~",
            "还有其他问题需要咨询吗？",
        ],
    }
    fallback_replies = [
        "抱歉，这个问题我需要转接人工客服为您解答。",
        "您的问题比较复杂，建议拨打客服热线400-XXX-XXXX详细咨询。",
        "正在为您转接专业顾问...",
    ]

    for _, sess in sess_df.iterrows():
        sid = sess["会话ID"]
        turns = int(sess["消息轮次"])
        intent = sess["主要意图"]
        channel = sess["会话渠道"]
        escalated = bool(sess["是否转人工"])
        esc_turn = int(sess["转人工轮次"]) if pd.notna(sess.get("转人工轮次")) and sess["转人工轮次"] else 0
        start_t = sess["会话开始时间"]
        is_resolved = bool(sess["是否已解决"])
        has_recommendation = bool(sess["是否包含产品推荐"])

        # Generate turn-by-turn
        cur_time = start_t
        sentiment_curve = _build_sentiment_curve(turns, is_resolved, rng)

        for turn in range(1, turns + 1):
            msg_counter += 1
            is_user_turn = (turn % 2 == 1)  # odd = user, even = AI

            # After escalation, human agent takes over some AI turns
            if escalated and esc_turn > 0 and turn >= esc_turn * 2:
                sender = "人工客服" if not is_user_turn else "用户"
            else:
                sender = "用户" if is_user_turn else "AI"

            resp_delay = None
            if turn > 1:
                resp_delay = round(rng.lognormal(0.8, 0.8) if sender != "系统" else 0.1, 2)

            # Build message content
            if sender == "用户":
                tmpls = user_templates.get(intent, user_templates["其他"])
                content = rng.choice(tmpls)
                # Fill placeholders
                content = content.replace("{product}", rng.choice(["百万医疗险","重疾险","意外险","定期寿险"]))
                content = content.replace("{age}", str(rng.integers(25, 55)))
            elif sender == "AI":
                tmpls = ai_templates.get(intent, ai_templates["其他"])
                content = rng.choice(tmpls)
                content = content.replace("{product}", rng.choice(["百万医疗险","重疾险","意外险","定期寿险"]))
                content = content.replace("{deductible}", rng.choice(["5000","10000","20000"]))
                content = content.replace("{waiting_days}", rng.choice(["30","60","90"]))
                content = content.replace("{coverage}", rng.choice(["覆盖住院医疗","覆盖住院+门诊"]))
                content = content.replace("{claim_days}", rng.choice(["3","5","7","10"]))
                content = content.replace("{network_count}", rng.choice(["2000","3000","5000"]))
                content = content.replace("{age}", str(rng.integers(25, 55)))
                content = content.replace("{premium}", f"{rng.integers(200, 5000)}")
                content = content.replace("{days}", rng.choice(["1-3","3-5"]))
                content = content.replace("{cash_value}", f"{rng.integers(500, 50000)}")
                content = content.replace("{ticket_id}", f"TK{rng.integers(100000, 999999)}")
            else:
                content = rng.choice(["您好，我是人工客服，请问有什么可以帮您？", "了解您的情况了，我马上帮您处理。"])

            # AI-specific fields
            ai_model_ver = None
            ai_confidence = None
            kb_refs = None
            use_rag = None
            rag_docs = None
            trigger_clarify = None
            trigger_fallback = None

            if sender == "AI":
                ai_model_ver = rng.choice(["conv-v2.1", "conv-v2.2", "conv-v3.0"])
                ai_confidence = round(rng.beta(7, 2), 4)
                use_rag = int(rng.random() < 0.5)
                rag_docs = rng.integers(1, 11) if use_rag else 0
                trigger_clarify = int(rng.random() < 0.1)
                trigger_fallback = int(rng.random() < 0.04)
                if trigger_fallback:
                    content = rng.choice(fallback_replies)
                kb_refs = json.dumps([_uid("KB", k) for k in rng.integers(100000, 999999, size=rng.integers(0, 4))], ensure_ascii=False)

            # Compliance
            compliance_filter = 0
            compliance_reason = None
            if rng.random() < 0.015:
                compliance_filter = 1
                compliance_reason = rng.choice(["夸大收益", "虚假承诺", "禁用语"])

            # User feedback
            user_feedback = None
            if not is_user_turn and rng.random() < 0.3:
                user_feedback = rng.choice(["有帮助", "无帮助", "未反馈"], p=[0.45, 0.15, 0.40])

            # Turn sentiment
            turn_sent = round(sentiment_curve[min(turn - 1, len(sentiment_curve) - 1)] * 2 - 1, 4)

            records.append({
                "消息ID": _uid("MSG", msg_counter, 12),
                "会话ID": sid,
                "消息序号": turn,
                "消息时间": cur_time,
                "发送者": sender,
                "消息类型": "文本" if rng.random() < 0.9 else rng.choice(["图片","文件","卡片","语音转文字"]),
                "消息内容": content,
                "本轮意图": intent if sender == "用户" else None,
                "本轮实体": json.dumps({"product": rng.choice(PRODUCT_LIST)[1]}, ensure_ascii=False) if sender == "用户" else None,
                "本轮情绪评分": turn_sent,
                "响应延迟": resp_delay,
                "AI模型版本": ai_model_ver,
                "AI置信度": ai_confidence,
                "知识库引用": kb_refs,
                "是否使用RAG": use_rag,
                "RAG检索文档数": rag_docs,
                "是否触发澄清": trigger_clarify,
                "是否触发兜底回复": trigger_fallback,
                "用户反馈标记": user_feedback,
                "合规过滤标记": compliance_filter,
                "合规过滤原因": compliance_reason,
                "消息向量embedding": None,
            })

            # Advance time
            cur_time = cur_time + _td(seconds=rng.lognormal(3.0, 1.5))

    df = pd.DataFrame(records)
    # Edge: 100 messages with compliance violation
    for i in rng.choice(len(df), size=min(100, len(df)), replace=False):
        df.loc[i, "合规过滤标记"] = 1
        df.loc[i, "合规过滤原因"] = rng.choice(["夸大收益","虚假承诺","禁用语"])
    # Edge: 80 low confidence
    for i in rng.choice(df[df["发送者"] == "AI"].index, size=min(80, len(df[df["发送者"] == "AI"])), replace=False):
        df.loc[i, "AI置信度"] = round(rng.beta(2, 5), 4)
    return df


def _build_sentiment_curve(turns: int, resolved: bool, rng) -> np.ndarray:
    """Build a realistic sentiment trajectory across conversation turns."""
    curve = np.zeros(turns)
    if turns == 1:
        curve[0] = rng.beta(4, 3)
        return curve
    start = rng.beta(4, 3)
    if resolved:
        end = min(1.0, start + rng.uniform(0.05, 0.3))
    else:
        end = max(0.05, start - rng.uniform(0.0, 0.25))
    for t in range(turns):
        progress = t / max(turns - 1, 1)
        noise = rng.normal(0, 0.05)
        curve[t] = np.clip(start + (end - start) * progress + noise, 0.01, 0.99)
    return curve


# ---------------------------------------------------------------------------
# Phase 10: 咨询结果追踪表
# ---------------------------------------------------------------------------

def generate_consultation_outcomes(sess_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 10: 咨询结果追踪表 ...")
    rng = np.random.default_rng(SEED)

    outcome_types = ["无动作", "产品购买", "理赔发起", "保单变更完成", "续保完成", "退保完成", "投诉工单", "流失"]
    outcome_weights = [0.40, 0.20, 0.10, 0.12, 0.08, 0.05, 0.03, 0.02]
    outcome_status_map = {
        "产品购买": ["已转化", "转化中", "未转化"],
        "理赔发起": ["已转化", "已关闭"],
        "保单变更完成": ["已转化", "已关闭"],
        "续保完成": ["已转化", "转化中"],
        "退保完成": ["已转化", "已关闭"],
        "投诉工单": ["已关闭"],
        "无动作": ["已关闭"],
        "流失": ["已流失"],
    }

    records = []
    for i, (_, sess) in enumerate(sess_df.iterrows()):
        sid = sess["会话ID"]
        cid = sess["客户ID"]
        sess_end = sess["会话结束时间"]
        if isinstance(sess_end, datetime.datetime):
            sess_date = sess_end.date()
        else:
            sess_date = TODAY

        track_date = sess_date + _td(days=rng.integers(0, 90))
        if track_date > TODAY:
            track_date = TODAY

        outcome = _weighted_choice(outcome_types, outcome_weights)
        status = rng.choice(outcome_status_map.get(outcome, ["已关闭"]))

        convert_days = None
        transaction_amt = None
        purchased_product = None
        rec_purchased = None
        if outcome == "产品购买" and status in ("已转化", "转化中"):
            convert_days = rng.integers(0, 90) if status == "已转化" else None
            transaction_amt = round(rng.lognormal(8.0, 1.0), 2)
            purchased_product = rng.choice(PRODUCT_LIST)[1]
            rec_purchased = int(rng.random() < 0.45)

        callback = int(rng.random() < 0.25)
        callback_sat = None
        nps = None
        if callback or rng.random() < 0.3:
            nps_roll = rng.random()
            if nps_roll < 0.30:
                nps = rng.integers(0, 7)  # detractor
            elif nps_roll < 0.50:
                nps = rng.integers(7, 9)  # passive
            else:
                nps = rng.integers(9, 11)  # promoter
            callback_sat = rng.integers(1, 6)

        complaint_escalated = int(outcome == "投诉工单")
        complaint_ticket = f"CT{rng.integers(100000, 999999)}" if complaint_escalated else None

        records.append({
            "结果追踪ID": _uid("OUTC", i + 1),
            "会话ID": sid,
            "客户ID": cid if pd.notna(cid) and cid else None,
            "追踪日期": track_date,
            "结果类型": outcome,
            "结果状态": status,
            "关联保单ID": "",
            "关联理赔ID": "",
            "转化时长": convert_days,
            "产品成交金额": transaction_amt,
            "是否推荐产品成交": rec_purchased,
            "成交产品编码": None,
            "客户回访标记": callback,
            "回访满意度": callback_sat,
            "NPS评分": nps,
            "是否投诉升级": complaint_escalated,
            "投诉工单号": complaint_ticket,
            "备注": "",
        })

    df = pd.DataFrame(records)
    # Edge: 10 with NPS=0
    for i in rng.choice(len(df), size=min(10, len(df)), replace=False):
        df.loc[i, "NPS评分"] = 0
    return df


# ---------------------------------------------------------------------------
# Phase 11: 常见问题知识库引用表
# ---------------------------------------------------------------------------

def generate_knowledge_references(msg_df: pd.DataFrame) -> pd.DataFrame:
    print("Phase 11: 常见问题知识库引用表 ...")
    rng = np.random.default_rng(SEED)

    # Only reference AI messages that used RAG
    ai_msgs = msg_df[(msg_df["发送者"] == "AI") & (msg_df["是否使用RAG"] == 1)]

    kb_titles = {
        "产品条款": ["百万医疗险免赔额说明","重疾险保障病种列表","意外险责任免除条款","寿险免责条款详解","年金险领取规则"],
        "理赔流程": ["理赔申请操作指南","理赔所需材料清单","理赔时效承诺说明","定点医院查询方法","异地就医理赔流程"],
        "保费规则": ["保费计算方式说明","缴费方式及周期说明","宽限期与复效规则","保费豁免条件","保证续保费率规则"],
        "健康告知": ["健康告知填写指南","常见既往症核保结论","智能核保操作说明","体检异常核保参考","高血压投保指引"],
        "投保须知": ["投保年龄限制说明","犹豫期权益说明","保险期间选择建议","受益人指定规则","自动续保设置说明"],
        "退保规则": ["退保流程及注意事项","现金价值计算方法","犹豫期退保说明","退保后再投保规则","部分退保操作指引"],
        "常见异议": ["价格比较回应话术","保障重复疑虑解答","理赔难顾虑回应","保险公司安全性说明"],
        "政策法规": ["保险法相关条款","健康保险管理办法","互联网保险监管规定","个人信息保护政策"],
    }

    records = []
    counter = 0
    for _, msg in ai_msgs.iterrows():
        mid = msg["消息ID"]
        sid = msg["会话ID"]
        n_refs = rng.integers(1, 4)
        for _ in range(n_refs):
            counter += 1
            kb_cat = rng.choice(KNOWLEDGE_CATEGORIES)
            kb_title = rng.choice(kb_titles.get(kb_cat, ["一般参考"]))
            retrieval = rng.choice(["语义检索","关键词匹配","规则路由","人工选择"], p=[0.50, 0.25, 0.15, 0.10])
            similarity = rng.beta(6, 2)
            adopted = int(similarity > 0.5 or rng.random() < 0.3)
            clicked = int(rng.random() < 0.3) if adopted else 0
            accurate = None if rng.random() < 0.8 else int(rng.random() < 0.9)

            records.append({
                "引用ID": _uid("KREF", counter),
                "消息ID": mid,
                "会话ID": sid,
                "知识条目ID": _uid("KB", rng.integers(100000, 999999), 6),
                "知识类别": kb_cat,
                "知识标题": kb_title,
                "检索方式": retrieval,
                "检索相似度": round(similarity, 4),
                "是否被采纳": adopted,
                "用户是否点击查看": clicked,
                "知识是否准确": accurate,
                "知识更新时间": _rand_date(datetime.date(2023, 1, 1), TODAY),
            })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Phase 1
    cust_df = generate_customer_profiles(N_CUSTOMERS)

    # Phase 2
    pol_df = generate_policy_master(cust_df, N_POLICIES)

    # Phase 3
    evt_df = generate_lifecycle_events(pol_df, cust_df, N_EVENTS)

    # Phase 4
    pay_df = generate_payment_records(pol_df, N_PAYMENTS)

    # Phase 5
    cov_df = generate_coverage_profiles(cust_df, pol_df)

    # Phase 6
    gap_df = generate_gap_results(cov_df)

    # Phase 7
    dlog_df = generate_gap_diagnosis_logs(cust_df, cov_df, gap_df)

    # Phase 8
    sess_df = generate_conversation_sessions(cust_df)

    # Phase 9
    msg_df = generate_conversation_messages(sess_df)

    # Phase 10
    out_df = generate_consultation_outcomes(sess_df)

    # Phase 11
    kref_df = generate_knowledge_references(msg_df)

    # Write all CSVs
    tables = {
        "客户画像表.csv": cust_df,
        "保单主表.csv": pol_df,
        "生命周期事件日志.csv": evt_df,
        "缴费记录表.csv": pay_df,
        "客户保障概况表.csv": cov_df,
        "保障缺口诊断结果表.csv": gap_df,
        "缺口诊断日志表.csv": dlog_df,
        "对话会话表.csv": sess_df,
        "对话消息明细表.csv": msg_df,
        "咨询结果追踪表.csv": out_df,
        "常见问题知识库引用表.csv": kref_df,
    }

    for fname, df in tables.items():
        path = OUTPUT_DIR / fname
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  [OK] {fname} — {len(df):,} rows, {len(df.columns)} columns")

    print(f"\nAll {len(tables)} tables written to {OUTPUT_DIR}")
    print(f"Total rows: {sum(len(df) for df in tables.values()):,}")


if __name__ == "__main__":
    main()
