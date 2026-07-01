"""
seed_demo.py — デモ用サンプルデータを DB に投入するスクリプト
スクレイパーが動かない環境でもフロントエンドの動作確認ができます。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from init_db import init_db
from scrape import upsert_events

DB_PATH = str(Path(__file__).parent.parent / "events.db")

DEMO_EVENTS = [
    {
        "title_ja": "宇宙線で覗く素粒子の世界",
        "title_en": "The World of Elementary Particles Seen Through Cosmic Rays",
        "date_start": "2025-10-24T10:00:00",
        "date_end": "2025-10-24T16:30:00",
        "venue_ja": "宇宙線研究所 本館 1階展示室",
        "venue_en": "ICRR Main Building, 1F Exhibition Room",
        "description_ja": "宇宙線の観測装置を実際に見ながら、素粒子物理学の最前線について研究者がわかりやすく解説します。スーパーカミオカンデの模型展示もあります。",
        "description_en": "Researchers explain the forefront of elementary particle physics through actual cosmic ray detectors. A scale model of Super-Kamiokande is also on display.",
        "researchers": json.dumps(["山本明", "鈴木洋一郎"], ensure_ascii=False),
        "researchers_en": json.dumps(["Akira Yamamoto", "Yoichiro Suzuki"], ensure_ascii=False),
        "target_audience_ja": "一般市民、小中高生",
        "target_audience_en": "General Public, K-12 Students",
        "registration_required": 0,
        "registration_url": "",
        "department_ja": "宇宙線研究所",
        "department_en": "Institute for Cosmic Ray Research (ICRR)",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo001",
    },
    {
        "title_ja": "海と大気の観測最前線 — 研究船の見学と気候変動の科学",
        "title_en": "Frontiers of Ocean and Atmosphere Observation — Research Vessel Tour and Climate Change Science",
        "date_start": "2025-10-24T10:00:00",
        "date_end": "2025-10-24T16:00:00",
        "venue_ja": "大気海洋研究所 屋外展示スペース",
        "venue_en": "Atmosphere and Ocean Research Institute, Outdoor Exhibition",
        "description_ja": "気候変動・海洋変動のメカニズムを研究する大気海洋研究所の研究成果を展示します。研究船の模型や観測機器の実物を展示し、研究者による講演も行います。",
        "description_en": "We showcase research on climate change and ocean variability, with scale models of research vessels, real observation instruments, and researcher talks.",
        "researchers": json.dumps(["谷本陽一", "大島慶一郎"], ensure_ascii=False),
        "researchers_en": json.dumps(["Yoichi Tanimoto", "Keiichiro Ohshima"], ensure_ascii=False),
        "target_audience_ja": "一般市民、大学生、研究者",
        "target_audience_en": "General Public, University Students, Researchers",
        "registration_required": 0,
        "registration_url": "",
        "department_ja": "大気海洋研究所",
        "department_en": "Atmosphere and Ocean Research Institute (AORI)",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo002",
    },
    {
        "title_ja": "暗黒物質の正体に迫る！カブリIPMU 最新研究展示",
        "title_en": "Closing in on Dark Matter! Kavli IPMU Latest Research Exhibition",
        "date_start": "2025-10-24T10:00:00",
        "date_end": "2025-10-25T16:30:00",
        "venue_ja": "カブリ数物連携宇宙研究機構 ロビー",
        "venue_en": "Kavli IPMU Lobby",
        "description_ja": "宇宙の謎「暗黒物質」「暗黒エネルギー」について、最新の研究成果をわかりやすく展示。ノーベル賞受賞者も所属する世界トップクラスの研究機関の最前線を体験できます。",
        "description_en": "Interactive exhibits on dark matter and dark energy in the universe, presented by one of the world's top research institutes, home to Nobel laureates.",
        "researchers": json.dumps(["村山斉", "大栗博司"], ensure_ascii=False),
        "researchers_en": json.dumps(["Hitoshi Murayama", "Hirosi Ooguri"], ensure_ascii=False),
        "target_audience_ja": "一般市民、小中高生、大学生",
        "target_audience_en": "General Public, K-12 Students, University Students",
        "registration_required": 0,
        "registration_url": "",
        "department_ja": "カブリ数物連携宇宙研究機構",
        "department_en": "Kavli Institute for the Physics and Mathematics of the Universe (Kavli IPMU)",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo003",
    },
    {
        "title_ja": "電子顕微鏡で見るナノの世界 — 物性研究所 施設公開",
        "title_en": "The Nano World Under an Electron Microscope — ISSP Facility Open Day",
        "date_start": "2025-10-25T10:00:00",
        "date_end": "2025-10-25T16:00:00",
        "venue_ja": "物性研究所 大型放射光施設棟",
        "venue_en": "Institute for Solid State Physics, Large-Scale Radiation Facility",
        "description_ja": "電子顕微鏡や放射光施設を使った最先端の材料科学研究を紹介。実際の研究装置を間近で見学でき、研究者が丁寧に解説します。中学生以上対象の体験コーナーもあります。",
        "description_en": "Introduction to cutting-edge materials science using electron microscopes and synchrotron radiation. Close-up views of real research equipment with researcher explanations. Hands-on corner for junior high students and above.",
        "researchers": json.dumps(["常行真司", "辛埴"], ensure_ascii=False),
        "researchers_en": json.dumps(["Shinji Tsuneyuki", "Iwao Matsuda"], ensure_ascii=False),
        "target_audience_ja": "一般市民、小中高生（中学生以上）",
        "target_audience_en": "General Public, K-12 Students (junior high and above)",
        "registration_required": 1,
        "registration_url": "https://www.issp.u-tokyo.ac.jp/open2025/",
        "department_ja": "物性研究所",
        "department_en": "Institute for Solid State Physics (ISSP)",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo004",
    },
    {
        "title_ja": "新領域創成科学の挑戦 — 学際研究の最前線",
        "title_en": "Challenges in Frontier Sciences — The Cutting Edge of Interdisciplinary Research",
        "date_start": "2025-10-24T13:00:00",
        "date_end": "2025-10-24T15:30:00",
        "venue_ja": "新領域創成科学研究科 講堂",
        "venue_en": "Graduate School of Frontier Sciences, Auditorium",
        "description_ja": "生命科学、環境科学、情報生命科学など多様な分野が融合した新領域創成科学研究科の研究成果を紹介する特別講演会。大学院進学を考える学部生にも最適です。",
        "description_en": "Special lecture series showcasing research at the Graduate School of Frontier Sciences, where life sciences, environmental sciences, and computational biology converge. Ideal for undergraduates considering graduate school.",
        "researchers": json.dumps(["榎戸輝揚", "加藤雄介", "津田真吾"], ensure_ascii=False),
        "researchers_en": json.dumps(["Teruaki Enoto", "Yusuke Kato", "Shingo Tsuda"], ensure_ascii=False),
        "target_audience_ja": "一般市民、大学生、研究者",
        "target_audience_en": "General Public, University Students, Researchers",
        "registration_required": 1,
        "registration_url": "https://www.k.u-tokyo.ac.jp/open2025/",
        "department_ja": "大学院新領域創成科学研究科",
        "department_en": "Graduate School of Frontier Sciences",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo005",
    },
    {
        "title_ja": "子どもサイエンス教室 — 光のふしぎを体験しよう",
        "title_en": "Children's Science Workshop — Discover the Wonders of Light",
        "date_start": "2025-10-25T10:30:00",
        "date_end": "2025-10-25T12:00:00",
        "venue_ja": "生産技術研究所 ワークショップルーム",
        "venue_en": "Institute of Industrial Science, Workshop Room",
        "description_ja": "光の分散・干渉・偏光などを体験できる子ども向けワークショップ。スペクトル観察や万華鏡づくりなど、楽しい実験を通して光の科学を学びます。小学3年生以上対象。",
        "description_en": "Hands-on workshop for children exploring dispersion, interference, and polarization of light. Activities include spectrum observation and kaleidoscope making. For 3rd graders and above.",
        "researchers": json.dumps([], ensure_ascii=False),
        "researchers_en": json.dumps([], ensure_ascii=False),
        "target_audience_ja": "小中高生（小学3年生以上）",
        "target_audience_en": "K-12 Students (3rd grade and above)",
        "registration_required": 1,
        "registration_url": "https://www.iis.u-tokyo.ac.jp/open2025/kids/",
        "department_ja": "生産技術研究所",
        "department_en": "Institute of Industrial Science (IIS)",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo006",
    },
    {
        "title_ja": "地図とGISで地球を読む — 空間情報科学の世界",
        "title_en": "Reading the Earth with Maps and GIS — The World of Spatial Information Science",
        "date_start": "2025-10-24T10:00:00",
        "date_end": "2025-10-24T16:30:00",
        "venue_ja": "空間情報科学研究センター 展示フロア",
        "venue_en": "Center for Spatial Information Science, Exhibition Floor",
        "description_ja": "衛星画像・GISを使った防災・都市計画・環境モニタリングの研究を紹介。インタラクティブな地図システムの体験コーナーも設置します。",
        "description_en": "Introduction to research using satellite imagery and GIS for disaster prevention, urban planning, and environmental monitoring. Interactive map system experience corner available.",
        "researchers": json.dumps(["柴崎亮介", "瀬戸寿一"], ensure_ascii=False),
        "researchers_en": json.dumps(["Ryosuke Shibasaki", "Hirokazu Seto"], ensure_ascii=False),
        "target_audience_ja": "一般市民、大学生",
        "target_audience_en": "General Public, University Students",
        "registration_required": 0,
        "registration_url": "",
        "department_ja": "空間情報科学研究センター",
        "department_en": "Center for Spatial Information Science (CSIS)",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo007",
    },
    {
        "title_ja": "スーパーコンピュータと情報科学の世界",
        "title_en": "Supercomputers and the World of Information Science",
        "date_start": "2025-10-25T10:00:00",
        "date_end": "2025-10-25T16:00:00",
        "venue_ja": "情報基盤センター 計算機室",
        "venue_en": "Information Technology Center, Computer Room",
        "description_ja": "東京大学の大型計算機システムを間近に見学。AIシミュレーション・気候計算・素粒子計算など最先端の計算科学を体験できます。",
        "description_en": "Close-up tour of UTokyo's large-scale computing systems. Experience cutting-edge computational science including AI simulation, climate calculations, and particle physics computation.",
        "researchers": json.dumps(["黒田久泰"], ensure_ascii=False),
        "researchers_en": json.dumps(["Hisayasu Kuroda"], ensure_ascii=False),
        "target_audience_ja": "一般市民、大学生、研究者",
        "target_audience_en": "General Public, University Students, Researchers",
        "registration_required": 0,
        "registration_url": "",
        "department_ja": "情報基盤センター",
        "department_en": "Information Technology Center",
        "source_url": "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/",
        "content_hash": "demo008",
    },
]


def seed():
    print(f"[seed] Initializing DB: {DB_PATH}")
    init_db(DB_PATH)
    new_count, updated_count = upsert_events(DEMO_EVENTS, DB_PATH)
    print(f"[seed] Done — New: {new_count}, Updated: {updated_count}")

    # 投入結果確認
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    print(f"[seed] Total events in DB: {total}")


if __name__ == "__main__":
    seed()
