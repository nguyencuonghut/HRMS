"""
Seed dữ liệu danh mục nghiệp vụ khác.

Phân lớp:
  - Required: loại hợp đồng, quốc tịch, dân tộc, tôn giáo, ngân hàng, loại nghỉ phép
  - Sample: kỹ năng, chứng chỉ, metadata mẫu hợp đồng/phụ lục và placeholder mẫu
"""

from hashlib import sha256

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.administrative_import_service import normalize_text
from app.services.contract_template_docx import PROJECT_ROOT


CONTRACT_CATEGORIES = [
    {
        "code": "labor_indefinite",
        "name": "HĐLĐ không xác định thời hạn",
        "document_kind": "labor_contract",
        "legal_contract_type": "indefinite_term",
        "business_group": "standard",
        "default_term_months": None,
        "sort_order": 10,
        "description": "Mẫu dùng cho hợp đồng lao động không xác định thời hạn.",
    },
    {
        "code": "labor_definite",
        "name": "HĐLĐ xác định thời hạn",
        "document_kind": "labor_contract",
        "legal_contract_type": "definite_term",
        "business_group": "standard",
        "default_term_months": 12,
        "sort_order": 20,
        "description": "Mẫu dùng cho hợp đồng lao động xác định thời hạn.",
    },
    {
        "code": "appendix_salary_change",
        "name": "Phụ lục điều chỉnh lương",
        "document_kind": "contract_appendix",
        "legal_contract_type": None,
        "business_group": "salary_change",
        "default_term_months": None,
        "sort_order": 30,
        "description": "Phụ lục ghi nhận thay đổi mức lương và phụ cấp trong hợp đồng.",
    },
    {
        "code": "appendix_job_change",
        "name": "Phụ lục điều chỉnh chức danh/công việc",
        "document_kind": "contract_appendix",
        "legal_contract_type": None,
        "business_group": "job_change",
        "default_term_months": None,
        "sort_order": 40,
        "description": "Phụ lục thay đổi chức danh, công việc hoặc nơi làm việc.",
    },
    {
        "code": "probation_agreement",
        "name": "Hợp đồng thử việc",
        "document_kind": "labor_contract",
        "legal_contract_type": None,
        "business_group": "probation",
        "default_term_months": 2,
        "sort_order": 25,
        "description": "Mẫu dùng cho thỏa thuận thử việc trước khi ký HĐLĐ chính thức.",
    },
]


NATIONALITIES = [
    # 241 quốc gia theo ISO 3166-1 — đối chiếu với sheet 'QuocTich' FileMau_D02_TK1_VNPT.xlsx
    # code = iso2_code (dùng làm khóa nội bộ và khóa VNPT)
    {"code": "AF", "name": "Afghanistan",                    "iso2_code": "AF", "iso3_code": "AFG"},
    {"code": "AL", "name": "Albania",                        "iso2_code": "AL", "iso3_code": "ALB"},
    {"code": "DZ", "name": "Algeria",                        "iso2_code": "DZ", "iso3_code": "DZA"},
    {"code": "AD", "name": "Andorra",                        "iso2_code": "AD", "iso3_code": "AND"},
    {"code": "AO", "name": "Angola",                         "iso2_code": "AO", "iso3_code": "AGO"},
    {"code": "AG", "name": "Antigua và Barbuda",             "iso2_code": "AG", "iso3_code": "ATG"},
    {"code": "AR", "name": "Argentina",                      "iso2_code": "AR", "iso3_code": "ARG"},
    {"code": "AM", "name": "Armenia",                        "iso2_code": "AM", "iso3_code": "ARM"},
    {"code": "AU", "name": "Australia",                      "iso2_code": "AU", "iso3_code": "AUS"},
    {"code": "AT", "name": "Áo",                             "iso2_code": "AT", "iso3_code": "AUT"},
    {"code": "AZ", "name": "Azerbaijan",                     "iso2_code": "AZ", "iso3_code": "AZE"},
    {"code": "BS", "name": "Bahamas",                        "iso2_code": "BS", "iso3_code": "BHS"},
    {"code": "BH", "name": "Bahrain",                        "iso2_code": "BH", "iso3_code": "BHR"},
    {"code": "BD", "name": "Bangladesh",                     "iso2_code": "BD", "iso3_code": "BGD"},
    {"code": "BB", "name": "Barbados",                       "iso2_code": "BB", "iso3_code": "BRB"},
    {"code": "BY", "name": "Belarus",                        "iso2_code": "BY", "iso3_code": "BLR"},
    {"code": "BE", "name": "Bỉ",                             "iso2_code": "BE", "iso3_code": "BEL"},
    {"code": "BZ", "name": "Belize",                         "iso2_code": "BZ", "iso3_code": "BLZ"},
    {"code": "BJ", "name": "Benin",                          "iso2_code": "BJ", "iso3_code": "BEN"},
    {"code": "BT", "name": "Bhutan",                         "iso2_code": "BT", "iso3_code": "BTN"},
    {"code": "BO", "name": "Bolivia",                        "iso2_code": "BO", "iso3_code": "BOL"},
    {"code": "BA", "name": "Bosnia và Herzegovina",          "iso2_code": "BA", "iso3_code": "BIH"},
    {"code": "BW", "name": "Botswana",                       "iso2_code": "BW", "iso3_code": "BWA"},
    {"code": "BR", "name": "Brazil",                         "iso2_code": "BR", "iso3_code": "BRA"},
    {"code": "BN", "name": "Brunei",                         "iso2_code": "BN", "iso3_code": "BRN"},
    {"code": "BG", "name": "Bulgaria",                       "iso2_code": "BG", "iso3_code": "BGR"},
    {"code": "BF", "name": "Burkina Faso",                   "iso2_code": "BF", "iso3_code": "BFA"},
    {"code": "BI", "name": "Burundi",                        "iso2_code": "BI", "iso3_code": "BDI"},
    {"code": "CV", "name": "Cabo Verde",                     "iso2_code": "CV", "iso3_code": "CPV"},
    {"code": "KH", "name": "Campuchia",                      "iso2_code": "KH", "iso3_code": "KHM"},
    {"code": "CM", "name": "Cameroon",                       "iso2_code": "CM", "iso3_code": "CMR"},
    {"code": "CA", "name": "Canada",                         "iso2_code": "CA", "iso3_code": "CAN"},
    {"code": "CF", "name": "Cộng hòa Trung Phi",            "iso2_code": "CF", "iso3_code": "CAF"},
    {"code": "TD", "name": "Chad",                           "iso2_code": "TD", "iso3_code": "TCD"},
    {"code": "CL", "name": "Chile",                          "iso2_code": "CL", "iso3_code": "CHL"},
    {"code": "CN", "name": "Trung Quốc",                     "iso2_code": "CN", "iso3_code": "CHN"},
    {"code": "CO", "name": "Colombia",                       "iso2_code": "CO", "iso3_code": "COL"},
    {"code": "KM", "name": "Comoros",                        "iso2_code": "KM", "iso3_code": "COM"},
    {"code": "CG", "name": "Cộng hòa Congo",                "iso2_code": "CG", "iso3_code": "COG"},
    {"code": "CD", "name": "Cộng hòa Dân chủ Congo",        "iso2_code": "CD", "iso3_code": "COD"},
    {"code": "CR", "name": "Costa Rica",                     "iso2_code": "CR", "iso3_code": "CRI"},
    {"code": "HR", "name": "Croatia",                        "iso2_code": "HR", "iso3_code": "HRV"},
    {"code": "CU", "name": "Cuba",                           "iso2_code": "CU", "iso3_code": "CUB"},
    {"code": "CY", "name": "Síp",                            "iso2_code": "CY", "iso3_code": "CYP"},
    {"code": "CZ", "name": "Cộng hòa Séc",                  "iso2_code": "CZ", "iso3_code": "CZE"},
    {"code": "DK", "name": "Đan Mạch",                       "iso2_code": "DK", "iso3_code": "DNK"},
    {"code": "DJ", "name": "Djibouti",                       "iso2_code": "DJ", "iso3_code": "DJI"},
    {"code": "DM", "name": "Dominica",                       "iso2_code": "DM", "iso3_code": "DMA"},
    {"code": "DO", "name": "Cộng hòa Dominican",            "iso2_code": "DO", "iso3_code": "DOM"},
    {"code": "EC", "name": "Ecuador",                        "iso2_code": "EC", "iso3_code": "ECU"},
    {"code": "EG", "name": "Ai Cập",                         "iso2_code": "EG", "iso3_code": "EGY"},
    {"code": "SV", "name": "El Salvador",                    "iso2_code": "SV", "iso3_code": "SLV"},
    {"code": "GQ", "name": "Guinea Xích Đạo",               "iso2_code": "GQ", "iso3_code": "GNQ"},
    {"code": "ER", "name": "Eritrea",                        "iso2_code": "ER", "iso3_code": "ERI"},
    {"code": "EE", "name": "Estonia",                        "iso2_code": "EE", "iso3_code": "EST"},
    {"code": "SZ", "name": "Eswatini",                       "iso2_code": "SZ", "iso3_code": "SWZ"},
    {"code": "ET", "name": "Ethiopia",                       "iso2_code": "ET", "iso3_code": "ETH"},
    {"code": "FJ", "name": "Fiji",                           "iso2_code": "FJ", "iso3_code": "FJI"},
    {"code": "FI", "name": "Phần Lan",                       "iso2_code": "FI", "iso3_code": "FIN"},
    {"code": "FR", "name": "Pháp",                           "iso2_code": "FR", "iso3_code": "FRA"},
    {"code": "GA", "name": "Gabon",                          "iso2_code": "GA", "iso3_code": "GAB"},
    {"code": "GM", "name": "Gambia",                         "iso2_code": "GM", "iso3_code": "GMB"},
    {"code": "GE", "name": "Gruzia",                         "iso2_code": "GE", "iso3_code": "GEO"},
    {"code": "DE", "name": "Đức",                            "iso2_code": "DE", "iso3_code": "DEU"},
    {"code": "GH", "name": "Ghana",                          "iso2_code": "GH", "iso3_code": "GHA"},
    {"code": "GR", "name": "Hy Lạp",                         "iso2_code": "GR", "iso3_code": "GRC"},
    {"code": "GD", "name": "Grenada",                        "iso2_code": "GD", "iso3_code": "GRD"},
    {"code": "GT", "name": "Guatemala",                      "iso2_code": "GT", "iso3_code": "GTM"},
    {"code": "GN", "name": "Guinea",                         "iso2_code": "GN", "iso3_code": "GIN"},
    {"code": "GW", "name": "Guinea-Bissau",                  "iso2_code": "GW", "iso3_code": "GNB"},
    {"code": "GY", "name": "Guyana",                         "iso2_code": "GY", "iso3_code": "GUY"},
    {"code": "HT", "name": "Haiti",                          "iso2_code": "HT", "iso3_code": "HTI"},
    {"code": "HN", "name": "Honduras",                       "iso2_code": "HN", "iso3_code": "HND"},
    {"code": "HU", "name": "Hungary",                        "iso2_code": "HU", "iso3_code": "HUN"},
    {"code": "IS", "name": "Iceland",                        "iso2_code": "IS", "iso3_code": "ISL"},
    {"code": "IN", "name": "Ấn Độ",                          "iso2_code": "IN", "iso3_code": "IND"},
    {"code": "ID", "name": "Indonesia",                      "iso2_code": "ID", "iso3_code": "IDN"},
    {"code": "IR", "name": "Iran",                           "iso2_code": "IR", "iso3_code": "IRN"},
    {"code": "IQ", "name": "Iraq",                           "iso2_code": "IQ", "iso3_code": "IRQ"},
    {"code": "IE", "name": "Ireland",                        "iso2_code": "IE", "iso3_code": "IRL"},
    {"code": "IL", "name": "Israel",                         "iso2_code": "IL", "iso3_code": "ISR"},
    {"code": "IT", "name": "Italy",                          "iso2_code": "IT", "iso3_code": "ITA"},
    {"code": "JM", "name": "Jamaica",                        "iso2_code": "JM", "iso3_code": "JAM"},
    {"code": "JP", "name": "Nhật Bản",                       "iso2_code": "JP", "iso3_code": "JPN"},
    {"code": "JO", "name": "Jordan",                         "iso2_code": "JO", "iso3_code": "JOR"},
    {"code": "KZ", "name": "Kazakhstan",                     "iso2_code": "KZ", "iso3_code": "KAZ"},
    {"code": "KE", "name": "Kenya",                          "iso2_code": "KE", "iso3_code": "KEN"},
    {"code": "KI", "name": "Kiribati",                       "iso2_code": "KI", "iso3_code": "KIR"},
    {"code": "KP", "name": "Triều Tiên",                     "iso2_code": "KP", "iso3_code": "PRK"},
    {"code": "KR", "name": "Hàn Quốc",                       "iso2_code": "KR", "iso3_code": "KOR"},
    {"code": "KW", "name": "Kuwait",                         "iso2_code": "KW", "iso3_code": "KWT"},
    {"code": "KG", "name": "Kyrgyzstan",                     "iso2_code": "KG", "iso3_code": "KGZ"},
    {"code": "LA", "name": "Lào",                            "iso2_code": "LA", "iso3_code": "LAO"},
    {"code": "LV", "name": "Latvia",                         "iso2_code": "LV", "iso3_code": "LVA"},
    {"code": "LB", "name": "Liban",                          "iso2_code": "LB", "iso3_code": "LBN"},
    {"code": "LS", "name": "Lesotho",                        "iso2_code": "LS", "iso3_code": "LSO"},
    {"code": "LR", "name": "Liberia",                        "iso2_code": "LR", "iso3_code": "LBR"},
    {"code": "LY", "name": "Libya",                          "iso2_code": "LY", "iso3_code": "LBY"},
    {"code": "LI", "name": "Liechtenstein",                  "iso2_code": "LI", "iso3_code": "LIE"},
    {"code": "LT", "name": "Lithuania",                      "iso2_code": "LT", "iso3_code": "LTU"},
    {"code": "LU", "name": "Luxembourg",                     "iso2_code": "LU", "iso3_code": "LUX"},
    {"code": "MG", "name": "Madagascar",                     "iso2_code": "MG", "iso3_code": "MDG"},
    {"code": "MW", "name": "Malawi",                         "iso2_code": "MW", "iso3_code": "MWI"},
    {"code": "MY", "name": "Malaysia",                       "iso2_code": "MY", "iso3_code": "MYS"},
    {"code": "MV", "name": "Maldives",                       "iso2_code": "MV", "iso3_code": "MDV"},
    {"code": "ML", "name": "Mali",                           "iso2_code": "ML", "iso3_code": "MLI"},
    {"code": "MT", "name": "Malta",                          "iso2_code": "MT", "iso3_code": "MLT"},
    {"code": "MH", "name": "Quần đảo Marshall",              "iso2_code": "MH", "iso3_code": "MHL"},
    {"code": "MR", "name": "Mauritania",                     "iso2_code": "MR", "iso3_code": "MRT"},
    {"code": "MU", "name": "Mauritius",                      "iso2_code": "MU", "iso3_code": "MUS"},
    {"code": "MX", "name": "Mexico",                         "iso2_code": "MX", "iso3_code": "MEX"},
    {"code": "FM", "name": "Micronesia",                     "iso2_code": "FM", "iso3_code": "FSM"},
    {"code": "MD", "name": "Moldova",                        "iso2_code": "MD", "iso3_code": "MDA"},
    {"code": "MC", "name": "Monaco",                         "iso2_code": "MC", "iso3_code": "MCO"},
    {"code": "MN", "name": "Mông Cổ",                        "iso2_code": "MN", "iso3_code": "MNG"},
    {"code": "ME", "name": "Montenegro",                     "iso2_code": "ME", "iso3_code": "MNE"},
    {"code": "MA", "name": "Maroc",                          "iso2_code": "MA", "iso3_code": "MAR"},
    {"code": "MZ", "name": "Mozambique",                     "iso2_code": "MZ", "iso3_code": "MOZ"},
    {"code": "MM", "name": "Myanmar",                        "iso2_code": "MM", "iso3_code": "MMR"},
    {"code": "NA", "name": "Namibia",                        "iso2_code": "NA", "iso3_code": "NAM"},
    {"code": "NR", "name": "Nauru",                          "iso2_code": "NR", "iso3_code": "NRU"},
    {"code": "NP", "name": "Nepal",                          "iso2_code": "NP", "iso3_code": "NPL"},
    {"code": "NL", "name": "Hà Lan",                         "iso2_code": "NL", "iso3_code": "NLD"},
    {"code": "NZ", "name": "New Zealand",                    "iso2_code": "NZ", "iso3_code": "NZL"},
    {"code": "NI", "name": "Nicaragua",                      "iso2_code": "NI", "iso3_code": "NIC"},
    {"code": "NE", "name": "Niger",                          "iso2_code": "NE", "iso3_code": "NER"},
    {"code": "NG", "name": "Nigeria",                        "iso2_code": "NG", "iso3_code": "NGA"},
    {"code": "NO", "name": "Na Uy",                          "iso2_code": "NO", "iso3_code": "NOR"},
    {"code": "OM", "name": "Oman",                           "iso2_code": "OM", "iso3_code": "OMN"},
    {"code": "PK", "name": "Pakistan",                       "iso2_code": "PK", "iso3_code": "PAK"},
    {"code": "PW", "name": "Palau",                          "iso2_code": "PW", "iso3_code": "PLW"},
    {"code": "PA", "name": "Panama",                         "iso2_code": "PA", "iso3_code": "PAN"},
    {"code": "PG", "name": "Papua New Guinea",               "iso2_code": "PG", "iso3_code": "PNG"},
    {"code": "PY", "name": "Paraguay",                       "iso2_code": "PY", "iso3_code": "PRY"},
    {"code": "PE", "name": "Peru",                           "iso2_code": "PE", "iso3_code": "PER"},
    {"code": "PH", "name": "Philippines",                    "iso2_code": "PH", "iso3_code": "PHL"},
    {"code": "PL", "name": "Ba Lan",                         "iso2_code": "PL", "iso3_code": "POL"},
    {"code": "PT", "name": "Bồ Đào Nha",                    "iso2_code": "PT", "iso3_code": "PRT"},
    {"code": "QA", "name": "Qatar",                          "iso2_code": "QA", "iso3_code": "QAT"},
    {"code": "RO", "name": "Romania",                        "iso2_code": "RO", "iso3_code": "ROU"},
    {"code": "RU", "name": "Nga",                            "iso2_code": "RU", "iso3_code": "RUS"},
    {"code": "RW", "name": "Rwanda",                         "iso2_code": "RW", "iso3_code": "RWA"},
    {"code": "KN", "name": "Saint Kitts và Nevis",           "iso2_code": "KN", "iso3_code": "KNA"},
    {"code": "LC", "name": "Saint Lucia",                    "iso2_code": "LC", "iso3_code": "LCA"},
    {"code": "VC", "name": "Saint Vincent và Grenadines",    "iso2_code": "VC", "iso3_code": "VCT"},
    {"code": "WS", "name": "Samoa",                          "iso2_code": "WS", "iso3_code": "WSM"},
    {"code": "SM", "name": "San Marino",                     "iso2_code": "SM", "iso3_code": "SMR"},
    {"code": "ST", "name": "São Tomé và Príncipe",           "iso2_code": "ST", "iso3_code": "STP"},
    {"code": "SA", "name": "Saudi Arabia",                   "iso2_code": "SA", "iso3_code": "SAU"},
    {"code": "SN", "name": "Senegal",                        "iso2_code": "SN", "iso3_code": "SEN"},
    {"code": "RS", "name": "Serbia",                         "iso2_code": "RS", "iso3_code": "SRB"},
    {"code": "SC", "name": "Seychelles",                     "iso2_code": "SC", "iso3_code": "SYC"},
    {"code": "SL", "name": "Sierra Leone",                   "iso2_code": "SL", "iso3_code": "SLE"},
    {"code": "SG", "name": "Singapore",                      "iso2_code": "SG", "iso3_code": "SGP"},
    {"code": "SK", "name": "Slovakia",                       "iso2_code": "SK", "iso3_code": "SVK"},
    {"code": "SI", "name": "Slovenia",                       "iso2_code": "SI", "iso3_code": "SVN"},
    {"code": "SB", "name": "Quần đảo Solomon",               "iso2_code": "SB", "iso3_code": "SLB"},
    {"code": "SO", "name": "Somalia",                        "iso2_code": "SO", "iso3_code": "SOM"},
    {"code": "ZA", "name": "Nam Phi",                        "iso2_code": "ZA", "iso3_code": "ZAF"},
    {"code": "SS", "name": "Nam Sudan",                      "iso2_code": "SS", "iso3_code": "SSD"},
    {"code": "ES", "name": "Tây Ban Nha",                    "iso2_code": "ES", "iso3_code": "ESP"},
    {"code": "LK", "name": "Sri Lanka",                      "iso2_code": "LK", "iso3_code": "LKA"},
    {"code": "SD", "name": "Sudan",                          "iso2_code": "SD", "iso3_code": "SDN"},
    {"code": "SR", "name": "Suriname",                       "iso2_code": "SR", "iso3_code": "SUR"},
    {"code": "SE", "name": "Thụy Điển",                      "iso2_code": "SE", "iso3_code": "SWE"},
    {"code": "CH", "name": "Thụy Sĩ",                        "iso2_code": "CH", "iso3_code": "CHE"},
    {"code": "SY", "name": "Syria",                          "iso2_code": "SY", "iso3_code": "SYR"},
    {"code": "TW", "name": "Đài Loan",                       "iso2_code": "TW", "iso3_code": "TWN"},
    {"code": "TJ", "name": "Tajikistan",                     "iso2_code": "TJ", "iso3_code": "TJK"},
    {"code": "TZ", "name": "Tanzania",                       "iso2_code": "TZ", "iso3_code": "TZA"},
    {"code": "TH", "name": "Thái Lan",                       "iso2_code": "TH", "iso3_code": "THA"},
    {"code": "TL", "name": "Timor-Leste",                    "iso2_code": "TL", "iso3_code": "TLS"},
    {"code": "TG", "name": "Togo",                           "iso2_code": "TG", "iso3_code": "TGO"},
    {"code": "TO", "name": "Tonga",                          "iso2_code": "TO", "iso3_code": "TON"},
    {"code": "TT", "name": "Trinidad và Tobago",             "iso2_code": "TT", "iso3_code": "TTO"},
    {"code": "TN", "name": "Tunisia",                        "iso2_code": "TN", "iso3_code": "TUN"},
    {"code": "TR", "name": "Thổ Nhĩ Kỳ",                    "iso2_code": "TR", "iso3_code": "TUR"},
    {"code": "TM", "name": "Turkmenistan",                   "iso2_code": "TM", "iso3_code": "TKM"},
    {"code": "TV", "name": "Tuvalu",                         "iso2_code": "TV", "iso3_code": "TUV"},
    {"code": "UG", "name": "Uganda",                         "iso2_code": "UG", "iso3_code": "UGA"},
    {"code": "UA", "name": "Ukraine",                        "iso2_code": "UA", "iso3_code": "UKR"},
    {"code": "AE", "name": "Các Tiểu Vương quốc Ả Rập",     "iso2_code": "AE", "iso3_code": "ARE"},
    {"code": "GB", "name": "Vương quốc Anh",                 "iso2_code": "GB", "iso3_code": "GBR"},
    {"code": "US", "name": "Hoa Kỳ",                         "iso2_code": "US", "iso3_code": "USA"},
    {"code": "UY", "name": "Uruguay",                        "iso2_code": "UY", "iso3_code": "URY"},
    {"code": "UZ", "name": "Uzbekistan",                     "iso2_code": "UZ", "iso3_code": "UZB"},
    {"code": "VU", "name": "Vanuatu",                        "iso2_code": "VU", "iso3_code": "VUT"},
    {"code": "VE", "name": "Venezuela",                      "iso2_code": "VE", "iso3_code": "VEN"},
    {"code": "VN", "name": "Việt Nam",                       "iso2_code": "VN", "iso3_code": "VNM"},
    {"code": "YE", "name": "Yemen",                          "iso2_code": "YE", "iso3_code": "YEM"},
    {"code": "ZM", "name": "Zambia",                         "iso2_code": "ZM", "iso3_code": "ZMB"},
    {"code": "ZW", "name": "Zimbabwe",                       "iso2_code": "ZW", "iso3_code": "ZWE"},
    # Thêm các quốc gia/vùng lãnh thổ còn lại để đủ 241 per VNPT QuocTich sheet
    {"code": "MK", "name": "Bắc Macedonia",                  "iso2_code": "MK", "iso3_code": "MKD"},
    {"code": "XK", "name": "Kosovo",                         "iso2_code": "XK", "iso3_code": "XKX"},
    {"code": "PS", "name": "Palestine",                      "iso2_code": "PS", "iso3_code": "PSE"},
    {"code": "TF", "name": "Lãnh thổ Nam Cực Pháp",         "iso2_code": "TF", "iso3_code": "ATF"},
    {"code": "AQ", "name": "Nam Cực",                        "iso2_code": "AQ", "iso3_code": "ATA"},
    {"code": "CK", "name": "Quần đảo Cook",                  "iso2_code": "CK", "iso3_code": "COK"},
    {"code": "CW", "name": "Curaçao",                        "iso2_code": "CW", "iso3_code": "CUW"},
    {"code": "FK", "name": "Quần đảo Falkland",              "iso2_code": "FK", "iso3_code": "FLK"},
    {"code": "FO", "name": "Quần đảo Faroe",                 "iso2_code": "FO", "iso3_code": "FRO"},
    {"code": "GF", "name": "Guiana thuộc Pháp",             "iso2_code": "GF", "iso3_code": "GUF"},
    {"code": "GI", "name": "Gibraltar",                      "iso2_code": "GI", "iso3_code": "GIB"},
    {"code": "GL", "name": "Greenland",                      "iso2_code": "GL", "iso3_code": "GRL"},
    {"code": "GP", "name": "Guadeloupe",                     "iso2_code": "GP", "iso3_code": "GLP"},
    {"code": "GU", "name": "Guam",                           "iso2_code": "GU", "iso3_code": "GUM"},
    {"code": "HK", "name": "Hồng Kông",                      "iso2_code": "HK", "iso3_code": "HKG"},
    {"code": "IM", "name": "Đảo Man",                        "iso2_code": "IM", "iso3_code": "IMN"},
    {"code": "IO", "name": "Lãnh thổ Ấn Độ Dương Anh",      "iso2_code": "IO", "iso3_code": "IOT"},
    {"code": "JE", "name": "Jersey",                         "iso2_code": "JE", "iso3_code": "JEY"},
    {"code": "MO", "name": "Macao",                          "iso2_code": "MO", "iso3_code": "MAC"},
    {"code": "MQ", "name": "Martinique",                     "iso2_code": "MQ", "iso3_code": "MTQ"},
    {"code": "MS", "name": "Montserrat",                     "iso2_code": "MS", "iso3_code": "MSR"},
    {"code": "NC", "name": "New Caledonia",                  "iso2_code": "NC", "iso3_code": "NCL"},
    {"code": "NU", "name": "Niue",                           "iso2_code": "NU", "iso3_code": "NIU"},
    {"code": "NF", "name": "Đảo Norfolk",                    "iso2_code": "NF", "iso3_code": "NFK"},
    {"code": "MP", "name": "Quần đảo Bắc Mariana",          "iso2_code": "MP", "iso3_code": "MNP"},
    {"code": "PF", "name": "Polynesia thuộc Pháp",          "iso2_code": "PF", "iso3_code": "PYF"},
    {"code": "PM", "name": "Saint Pierre và Miquelon",       "iso2_code": "PM", "iso3_code": "SPM"},
    {"code": "PN", "name": "Đảo Pitcairn",                   "iso2_code": "PN", "iso3_code": "PCN"},
    {"code": "PR", "name": "Puerto Rico",                    "iso2_code": "PR", "iso3_code": "PRI"},
    {"code": "RE", "name": "Réunion",                        "iso2_code": "RE", "iso3_code": "REU"},
    {"code": "SH", "name": "Saint Helena",                   "iso2_code": "SH", "iso3_code": "SHN"},
    {"code": "SJ", "name": "Svalbard và Jan Mayen",          "iso2_code": "SJ", "iso3_code": "SJM"},
    {"code": "SX", "name": "Sint Maarten",                   "iso2_code": "SX", "iso3_code": "SXM"},
    {"code": "TC", "name": "Quần đảo Turks và Caicos",       "iso2_code": "TC", "iso3_code": "TCA"},
    {"code": "TK", "name": "Tokelau",                        "iso2_code": "TK", "iso3_code": "TKL"},
    {"code": "UM", "name": "Các đảo nhỏ xa xôi của Hoa Kỳ", "iso2_code": "UM", "iso3_code": "UMI"},
    {"code": "VI", "name": "Quần đảo Virgin (Mỹ)",           "iso2_code": "VI", "iso3_code": "VIR"},
    {"code": "VG", "name": "Quần đảo Virgin (Anh)",          "iso2_code": "VG", "iso3_code": "VGB"},
    {"code": "WF", "name": "Wallis và Futuna",               "iso2_code": "WF", "iso3_code": "WLF"},
    {"code": "EH", "name": "Tây Sahara",                     "iso2_code": "EH", "iso3_code": "ESH"},
    {"code": "YT", "name": "Mayotte",                        "iso2_code": "YT", "iso3_code": "MYT"},
]


ETHNICITIES = [
    # 54 dân tộc chính thức (mã số VNPT 01-54) — theo danh sách QĐ 121-HĐBT/1981
    # + mã 55 (Cà Dong) và 99 (Nước ngoài) từ sheet 'Dân tộc' FileMau_D02_TK1_VNPT.xlsx
    # code = mã nội bộ hệ thống (giữ nguyên để không phá FK đang tồn tại)
    # bhxh_code = mã 2 chữ số dùng khi export D02-TS VNPT
    {"code": "KINH",       "name": "Kinh",           "bhxh_code": "01"},
    {"code": "TAY",        "name": "Tày",             "bhxh_code": "02"},
    {"code": "THAI",       "name": "Thái",            "bhxh_code": "03"},
    {"code": "MUONG",      "name": "Mường",           "bhxh_code": "04"},
    {"code": "KHMER",      "name": "Khmer",           "bhxh_code": "05"},
    {"code": "HMONG",      "name": "H'Mông",          "bhxh_code": "06"},
    {"code": "NUNG",       "name": "Nùng",            "bhxh_code": "07"},
    {"code": "HOA",        "name": "Hoa",             "bhxh_code": "08"},
    {"code": "DAO",        "name": "Dao",             "bhxh_code": "09"},
    {"code": "GIA_RAI",    "name": "Gia Rai",         "bhxh_code": "10"},
    {"code": "EDE",        "name": "Ê Đê",            "bhxh_code": "11"},
    {"code": "BA_NA",      "name": "Ba Na",           "bhxh_code": "12"},
    {"code": "XO_DANG",    "name": "Xơ Đăng",        "bhxh_code": "13"},
    {"code": "SAN_CHAY",   "name": "Sán Chay",        "bhxh_code": "14"},
    {"code": "CO_HO",      "name": "Cơ Ho",           "bhxh_code": "15"},
    {"code": "CHAM",       "name": "Chăm",            "bhxh_code": "16"},
    {"code": "SAN_DIU",    "name": "Sán Dìu",         "bhxh_code": "17"},
    {"code": "HRE",        "name": "Hrê",             "bhxh_code": "18"},
    {"code": "MNONG",      "name": "Mnông",           "bhxh_code": "19"},
    {"code": "RAGLAY",     "name": "Raglai",          "bhxh_code": "20"},
    {"code": "XTIENG",     "name": "Xtiêng",          "bhxh_code": "21"},
    {"code": "BRU_VAN_KIEU", "name": "Bru - Vân Kiều", "bhxh_code": "22"},
    {"code": "THO",        "name": "Thổ",             "bhxh_code": "23"},
    {"code": "GIAY",       "name": "Giáy",            "bhxh_code": "24"},
    {"code": "CO_TU",      "name": "Cơ Tu",           "bhxh_code": "25"},
    {"code": "GIE_TRIENG", "name": "Gié - Triêng",   "bhxh_code": "26"},
    {"code": "MA",         "name": "Mạ",              "bhxh_code": "27"},
    {"code": "KHO_MU",     "name": "Khơ Mú",         "bhxh_code": "28"},
    {"code": "CO",         "name": "Co",              "bhxh_code": "29"},
    {"code": "TA_OI",      "name": "Ta Ôi",           "bhxh_code": "30"},
    {"code": "CHO_RO",     "name": "Chơ Ro",          "bhxh_code": "31"},
    {"code": "KHANG",      "name": "Kháng",           "bhxh_code": "32"},
    {"code": "XINH_MUN",   "name": "Xinh Mun",        "bhxh_code": "33"},
    {"code": "HA_NHI",     "name": "Hà Nhì",          "bhxh_code": "34"},
    {"code": "CHU_RU",     "name": "Chu Ru",          "bhxh_code": "35"},
    {"code": "LAO",        "name": "Lào",             "bhxh_code": "36"},
    {"code": "LA_CHI",     "name": "La Chí",          "bhxh_code": "37"},
    {"code": "LA_HA",      "name": "La Ha",           "bhxh_code": "38"},
    {"code": "PHU_LA",     "name": "Phù Lá",          "bhxh_code": "39"},
    {"code": "LA_HU",      "name": "La Hủ",           "bhxh_code": "40"},
    {"code": "LU",         "name": "Lự",              "bhxh_code": "41"},
    {"code": "LO_LO",      "name": "Lô Lô",           "bhxh_code": "42"},
    {"code": "CHUT",       "name": "Chứt",            "bhxh_code": "43"},
    {"code": "MANG",       "name": "Mảng",            "bhxh_code": "44"},
    {"code": "PA_THEN",    "name": "Pà Thẻn",         "bhxh_code": "45"},
    {"code": "CO_LAO",     "name": "Co Lao",          "bhxh_code": "46"},
    {"code": "CONG",       "name": "Cống",            "bhxh_code": "47"},
    {"code": "BO_Y",       "name": "Bố Y",            "bhxh_code": "48"},
    {"code": "SI_LA",      "name": "Si La",           "bhxh_code": "49"},
    {"code": "PU_PEO",     "name": "Pu Péo",          "bhxh_code": "50"},
    {"code": "RO_MAM",     "name": "Rơ Măm",          "bhxh_code": "51"},
    {"code": "BRAU",       "name": "Brâu",            "bhxh_code": "52"},
    {"code": "O_DU",       "name": "Ơ Đu",            "bhxh_code": "53"},
    {"code": "NGAI",       "name": "Ngái",            "bhxh_code": "54"},
    {"code": "CA_DONG",    "name": "Cà Dong",         "bhxh_code": "55"},  # VNPT bổ sung
    {"code": "NUOC_NGOAI", "name": "Nước ngoài",      "bhxh_code": "99"},  # Người nước ngoài
]


RELIGIONS = [
    {"code": "NONE", "name": "Không"},
    {"code": "PHAT_GIAO", "name": "Phật giáo"},
    {"code": "CONG_GIAO", "name": "Công giáo"},
    {"code": "TINH_LANH", "name": "Tin Lành"},
    {"code": "CAO_DAI", "name": "Cao Đài"},
    {"code": "HOA_HAO", "name": "Phật giáo Hòa Hảo"},
]


BANKS = [
    {"code": "AGRIBANK", "name": "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", "short_name": "Agribank", "bin_code": "970405", "swift_code": "VBAAVNVX"},
    {"code": "VCB", "name": "Ngân hàng TMCP Ngoại thương Việt Nam", "short_name": "Vietcombank", "bin_code": "970436", "swift_code": "BFTVVNVX"},
    {"code": "BIDV", "name": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "short_name": "BIDV", "bin_code": "970418", "swift_code": "BIDVVNVX"},
    {"code": "VIETINBANK", "name": "Ngân hàng TMCP Công thương Việt Nam", "short_name": "VietinBank", "bin_code": "970415", "swift_code": "ICBVVNVX"},
    {"code": "TECHCOMBANK", "name": "Ngân hàng TMCP Kỹ thương Việt Nam", "short_name": "Techcombank", "bin_code": "970407", "swift_code": "VTCBVNVX"},
    {"code": "MB", "name": "Ngân hàng TMCP Quân đội", "short_name": "MB Bank", "bin_code": "970422", "swift_code": "MSCBVNVX"},
    {"code": "ACB", "name": "Ngân hàng TMCP Á Châu", "short_name": "ACB", "bin_code": "970416", "swift_code": None},
    {"code": "SACOMBANK", "name": "Ngân hàng TMCP Sài Gòn Thương Tín", "short_name": "Sacombank", "bin_code": "970403", "swift_code": "SGTTVNVX"},
]


LEAVE_TYPES = [
    {
        "code": "annual_leave",
        "name": "Phép năm",
        "is_paid_leave": True,
        "affects_annual_leave": True,
        "allow_half_day": True,
        "requires_attachment": False,
        "color_tag": "green",
        "description": "Nghỉ phép năm theo số dư phép của nhân viên. 12 ngày/năm (Điều 113 BLĐ 2019), +1 ngày/5 năm thâm niên.",
        # Ngày lễ trùng phép không trừ quota (Điều 112 BLĐ 2019)
        "count_public_holidays": False,
        "max_days_per_year": None,
        "max_consecutive_days": None,
        "min_advance_days": 1,
        "carryover_allowed": True,
        "carryover_cutoff_month": 3,  # Hết Q1 năm sau
    },
    {
        "code": "sick_leave",
        "name": "Nghỉ bệnh",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": True,
        "requires_attachment": True,
        "color_tag": "orange",
        "description": "Nghỉ bệnh — BHXH trả (30–75 ngày/năm tùy thâm niên đóng BHXH, Điều 26 Luật BHXH).",
        "count_public_holidays": True,
        "max_days_per_year": None,
        "max_consecutive_days": None,
        "min_advance_days": 0,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
    {
        "code": "maternity_leave",
        "name": "Nghỉ thai sản nữ",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": True,
        "color_tag": "pink",
        "description": "Nghỉ thai sản nữ 6 tháng (Điều 139 BLĐ 2019), BHXH trả 100% lương bình quân.",
        "count_public_holidays": True,
        "max_days_per_year": None,
        "max_consecutive_days": 180,
        "min_advance_days": 0,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
    {
        "code": "paternity_leave",
        "name": "Nghỉ thai sản nam",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": True,
        "color_tag": "blue",
        "description": "Nghỉ thai sản nam (Điều 34 Luật BHXH): vợ đẻ thường 5 ngày, phẫu thuật/non tháng 7 ngày, sinh đôi 10 ngày, sinh ba 14 ngày.",
        "count_public_holidays": True,
        "max_days_per_year": 14,
        "max_consecutive_days": 14,
        "min_advance_days": 0,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
    {
        "code": "child_care_leave",
        "name": "Nghỉ chăm sóc con ốm",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": True,
        "color_tag": "cyan",
        "description": "Nghỉ chăm sóc con ốm (Điều 27 Luật BHXH): con < 3 tuổi 20 ngày/năm, con 3–7 tuổi 15 ngày/năm. BHXH trả.",
        "count_public_holidays": True,
        "max_days_per_year": 20,
        "max_consecutive_days": None,
        "min_advance_days": 0,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
    {
        "code": "bereavement_leave",
        "name": "Nghỉ tang",
        "is_paid_leave": True,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": False,
        "color_tag": "slate",
        "description": "Nghỉ tang (Điều 115 BLĐ 2019): 3 ngày (bố/mẹ/vợ/chồng/con), 1 ngày (ông/bà/anh/chị/em).",
        "count_public_holidays": True,
        "max_days_per_year": 3,
        "max_consecutive_days": 3,
        "min_advance_days": 0,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
    {
        "code": "marriage_leave",
        "name": "Nghỉ cưới",
        "is_paid_leave": True,
        "affects_annual_leave": False,
        "allow_half_day": False,
        "requires_attachment": False,
        "color_tag": "violet",
        "description": "Nghỉ cưới (Điều 115 BLĐ 2019): 3 ngày (bản thân kết hôn), 1 ngày (con kết hôn).",
        "count_public_holidays": True,
        "max_days_per_year": 3,
        "max_consecutive_days": 3,
        "min_advance_days": 0,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
    {
        "code": "unpaid_leave",
        "name": "Nghỉ không lương",
        "is_paid_leave": False,
        "affects_annual_leave": False,
        "allow_half_day": True,
        "requires_attachment": False,
        "color_tag": "gray",
        "description": "Nghỉ không hưởng lương theo thỏa thuận giữa người lao động và người sử dụng lao động.",
        "count_public_holidays": True,
        "max_days_per_year": None,
        "max_consecutive_days": None,
        "min_advance_days": 1,
        "carryover_allowed": False,
        "carryover_cutoff_month": 3,
    },
]


SKILLS = [
    {"code": "production_operation", "name": "Vận hành sản xuất", "skill_group": "production"},
    {"code": "feed_formulation", "name": "Xây dựng công thức thức ăn chăn nuôi", "skill_group": "production"},
    {"code": "raw_material_testing", "name": "Kiểm nghiệm nguyên liệu", "skill_group": "quality"},
    {"code": "qa_qc", "name": "QA/QC", "skill_group": "quality"},
    {"code": "farm_management", "name": "Quản lý trang trại", "skill_group": "farm"},
    {"code": "biosecurity", "name": "An toàn sinh học", "skill_group": "farm"},
    {"code": "veterinary_practice", "name": "Nghiệp vụ thú y", "skill_group": "farm"},
    {"code": "import_export_ops", "name": "Nghiệp vụ xuất nhập khẩu", "skill_group": "supply_chain"},
    {"code": "customs_declaration", "name": "Khai báo hải quan", "skill_group": "supply_chain"},
    {"code": "logistics_planning", "name": "Điều phối logistics", "skill_group": "supply_chain"},
]


CERTIFICATES = [
    {
        "code": "OSH",
        "name": "Chứng nhận An toàn vệ sinh lao động",
        "certificate_group": "safety",
        "issuer_name": "Đơn vị đào tạo được cấp phép",
        "expiry_policy": "months_after_issue",
        "default_valid_months": 24,
    },
    {
        "code": "HACCP",
        "name": "Chứng nhận HACCP",
        "certificate_group": "quality",
        "issuer_name": "Tổ chức chứng nhận phù hợp",
        "expiry_policy": "fixed_date",
        "default_valid_months": 36,
    },
    {
        "code": "ISO_22000",
        "name": "Chứng nhận ISO 22000",
        "certificate_group": "quality",
        "issuer_name": "Tổ chức chứng nhận phù hợp",
        "expiry_policy": "fixed_date",
        "default_valid_months": 36,
    },
    {
        "code": "VETERINARY_PRACTICE",
        "name": "Chứng chỉ hành nghề thú y",
        "certificate_group": "farm",
        "issuer_name": "Cơ quan có thẩm quyền",
        "expiry_policy": "fixed_date",
        "default_valid_months": 60,
    },
    {
        "code": "CUSTOMS_DECLARATION",
        "name": "Chứng chỉ nghiệp vụ khai báo hải quan",
        "certificate_group": "supply_chain",
        "issuer_name": "Cơ sở đào tạo được công nhận",
        "expiry_policy": "none",
        "default_valid_months": None,
    },
]


CONTRACT_TEMPLATES = [
    {
        "code": "ld_indefinite",
        "name": "Mẫu HĐLĐ không xác định thời hạn",
        "contract_category_code": "labor_indefinite",
        "document_kind": "labor_contract",
        "template_engine": "docx_placeholders",
        "file_name": "hdld_khong_xac_dinh_thoi_han_v1.docx",
        "storage_path": "app/seeds/data/hdld_khong_xac_dinh_thoi_han_v1.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Mẫu DOCX tham khảo lấy từ thư mục templates, dùng để quét placeholder thật.",
    },
    {
        "code": "ld_definite_12m",
        "name": "Mẫu HĐLĐ xác định thời hạn 12 tháng",
        "contract_category_code": "labor_definite",
        "document_kind": "labor_contract",
        "template_engine": "docx_placeholders",
        "file_name": "fixed_term.docx",
        "storage_path": "app/seeds/data/fixed_term.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Mẫu DOCX tham khảo lấy từ thư mục templates, dùng để quét placeholder thật.",
    },
    {
        "code": "probation_standard",
        "name": "Mẫu hợp đồng thử việc chuẩn",
        "contract_category_code": "probation_agreement",
        "document_kind": "labor_contract",
        "template_engine": "docx_placeholders",
        "file_name": "probation.docx",
        "storage_path": "app/seeds/data/probation.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Mẫu DOCX tham khảo lấy từ thư mục templates, dùng để quét placeholder thật.",
    },
    {
        "code": "appendix_salary_change",
        "name": "Mẫu phụ lục điều chỉnh lương",
        "contract_category_code": "appendix_salary_change",
        "document_kind": "contract_appendix",
        "template_engine": "docx_placeholders",
        "file_name": "phu_luc_dieu_chinh_luong_v1.docx",
        "storage_path": None,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "file_size": None,
        "file_checksum": None,
        "version_no": 1,
        "note": "Metadata seed ban đầu, chờ upload file mẫu Word thật.",
    },
]


CONTRACT_TEMPLATE_PLACEHOLDERS = {
    "ld_indefinite": [
        ("contract_number", "Số hợp đồng", "contract_draft", "contract.contract_number", "text", None, True, None, 10),
        ("employee_full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 20),
        ("employee_birthday", "Ngày sinh", "employee", "employee.date_of_birth", "date", "vn_date", True, None, 30),
        ("employee_cccd", "Số CCCD", "employee", "employee.identity_number", "text", None, True, None, 40),
        ("employee_cccd_issued_on", "Ngày cấp CCCD", "employee", "employee.identity_issued_on", "date", "vn_date", False, None, 50),
        ("employee_cccd_issued_by", "Nơi cấp CCCD", "employee", "employee.identity_issued_by", "text", None, False, None, 60),
        ("employee_address", "Địa chỉ thường trú", "employee", "employee.permanent_address_full", "text", None, False, None, 70),
        ("employee_temp_address", "Địa chỉ hiện tại", "employee", "employee.current_address_full", "text", None, False, None, 80),
        ("employee_phone", "Số điện thoại", "employee", "employee.phone_number", "text", None, False, None, 90),
        ("employee_personal_email", "Email cá nhân", "employee", "employee.personal_email", "text", None, False, None, 100),
        ("employee_gender", "Giới tính", "employee", "employee.gender_label", "text", None, False, None, 110),
        ("contract_start_date", "Ngày bắt đầu hợp đồng", "contract_draft", "contract.start_date", "date", "vn_date", True, None, 120),
        ("position_title", "Chức danh công việc", "employee", "employee.position_name", "text", None, True, None, 130),
        ("department_name", "Phòng ban", "employee", "employee.department_name", "text", None, True, None, 140),
        ("insurance_salary", "Lương BHXH", "contract_draft", "contract.insurance_salary", "currency", "currency_vnd", False, None, 150),
    ],
    "ld_definite_12m": [
        ("contract_number", "Số hợp đồng", "contract_draft", "contract.contract_number", "text", None, True, None, 10),
        ("employee_full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 20),
        ("employee_birthday", "Ngày sinh", "employee", "employee.date_of_birth", "date", "vn_date", True, None, 30),
        ("employee_cccd", "Số CCCD", "employee", "employee.identity_number", "text", None, True, None, 40),
        ("employee_cccd_issued_on", "Ngày cấp CCCD", "employee", "employee.identity_issued_on", "date", "vn_date", False, None, 50),
        ("employee_cccd_issued_by", "Nơi cấp CCCD", "employee", "employee.identity_issued_by", "text", None, False, None, 60),
        ("employee_address", "Địa chỉ thường trú", "employee", "employee.permanent_address_full", "text", None, False, None, 70),
        ("employee_temp_address", "Địa chỉ hiện tại", "employee", "employee.current_address_full", "text", None, False, None, 80),
        ("employee_phone", "Số điện thoại", "employee", "employee.phone_number", "text", None, False, None, 90),
        ("employee_personal_email", "Email cá nhân", "employee", "employee.personal_email", "text", None, False, None, 100),
        ("employee_gender", "Giới tính", "employee", "employee.gender_label", "text", None, False, None, 110),
        ("department_name", "Phòng ban", "employee", "employee.department_name", "text", None, True, None, 120),
        ("position_title", "Chức danh công việc", "employee", "employee.position_name", "text", None, True, None, 130),
        ("contract_start_date", "Ngày bắt đầu hợp đồng", "contract_draft", "contract.start_date", "date", "vn_date", True, None, 140),
        ("contract_end_date", "Ngày kết thúc hợp đồng", "contract_draft", "contract.end_date", "date", "vn_date", False, None, 150),
        ("insurance_salary", "Lương BHXH", "contract_draft", "contract.insurance_salary", "currency", "currency_vnd", False, None, 160),
        ("Ngày", "Ngày ký (ngày)", "system", "system.render_date.day", "number", None, False, None, 170),
        ("Tháng", "Ngày ký (tháng)", "system", "system.render_date.month", "number", None, False, None, 180),
        ("Năm", "Ngày ký (năm)", "system", "system.render_date.year", "number", None, False, None, 190),
        ("SĐT", "Số điện thoại", "employee", "employee.phone_number", "text", None, False, None, 200),
        ("Loại_HĐLĐ__", "Loại hợp đồng", "contract_draft", "contract.contract_type_label", "text", None, False, None, 210),
        ("Thời_hạn_trả_lương", "Kỳ hạn trả lương", "contract_draft", "contract.pay_cycle_label", "text", None, False, None, 220),
    ],
    "probation_standard": [
        ("contract_number", "Số hợp đồng", "contract_draft", "contract.contract_number", "text", None, True, None, 10),
        ("employee_full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 20),
        ("employee_birthday", "Ngày sinh", "employee", "employee.date_of_birth", "date", "vn_date", True, None, 30),
        ("employee_cccd", "Số CCCD", "employee", "employee.identity_number", "text", None, True, None, 40),
        ("employee_cccd_issued_on", "Ngày cấp CCCD", "employee", "employee.identity_issued_on", "date", "vn_date", False, None, 50),
        ("employee_cccd_issued_by", "Nơi cấp CCCD", "employee", "employee.identity_issued_by", "text", None, False, None, 60),
        ("employee_address", "Địa chỉ thường trú", "employee", "employee.permanent_address_full", "text", None, False, None, 70),
        ("employee_temp_address", "Địa chỉ hiện tại", "employee", "employee.current_address_full", "text", None, False, None, 80),
        ("employee_phone", "Số điện thoại", "employee", "employee.phone_number", "text", None, False, None, 90),
        ("employee_personal_email", "Email cá nhân", "employee", "employee.personal_email", "text", None, False, None, 100),
        ("position_title", "Chức danh công việc", "employee", "employee.position_name", "text", None, True, None, 110),
        ("contract_start_date", "Ngày bắt đầu thử việc", "contract_draft", "contract.start_date", "date", "vn_date", True, None, 120),
        ("contract_end_date", "Ngày kết thúc thử việc", "contract_draft", "contract.end_date", "date", "vn_date", False, None, 130),
        ("insurance_salary", "Lương thử việc/BHXH", "contract_draft", "contract.insurance_salary", "currency", "currency_vnd", False, None, 140),
        ("insurance_salary_words", "Lương bằng chữ", "contract_draft", "contract.insurance_salary_words", "text", None, False, None, 150),
    ],
    "appendix_salary_change": [
        ("employee.full_name", "Họ và tên", "employee", "employee.full_name", "text", None, True, None, 10),
        ("contract.contract_number", "Số HĐ gốc", "contract_draft", "contract.contract_number", "text", None, True, None, 20),
        ("appendix.effective_date", "Ngày áp dụng", "contract_draft", "appendix.effective_date", "date", "vn_date", True, None, 30),
        ("appendix.old_salary", "Lương cũ", "contract_draft", "appendix.old_salary", "currency", "currency_vnd", True, None, 40),
        ("appendix.new_salary", "Lương mới", "contract_draft", "appendix.new_salary", "currency", "currency_vnd", True, None, 50),
    ],
}


def _normalize(value: str) -> str:
    return normalize_text(value)


def _template_file_meta(storage_path: str | None) -> tuple[int | None, str | None]:
    if not storage_path:
        return None, None
    file_path = PROJECT_ROOT / storage_path
    if not file_path.exists():
        return None, None
    payload = file_path.read_bytes()
    return len(payload), sha256(payload).hexdigest()


async def seed_required_other_business_catalog(session: AsyncSession) -> tuple[int, int, int, int, int, int]:
    contract_categories_added = 0
    nationalities_added = 0
    ethnicities_added = 0
    religions_added = 0
    banks_added = 0
    leave_types_added = 0

    for item in CONTRACT_CATEGORIES:
        result = await session.execute(
            text(
                """
                INSERT INTO contract_categories
                    (code, name, normalized_name, document_kind, legal_contract_type, business_group,
                     default_term_months, sort_order, is_active, description)
                VALUES
                    (:code, :name, :normalized_name, :document_kind, :legal_contract_type, :business_group,
                     :default_term_months, :sort_order, true, :description)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    document_kind = EXCLUDED.document_kind,
                    legal_contract_type = EXCLUDED.legal_contract_type,
                    business_group = EXCLUDED.business_group,
                    default_term_months = EXCLUDED.default_term_months,
                    sort_order = EXCLUDED.sort_order,
                    is_active = true,
                    description = EXCLUDED.description
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        contract_categories_added += result.rowcount

    for item in NATIONALITIES:
        result = await session.execute(
            text(
                """
                INSERT INTO nationalities (code, name, normalized_name, iso2_code, iso3_code, is_active)
                VALUES (:code, :name, :normalized_name, :iso2_code, :iso3_code, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    iso2_code = EXCLUDED.iso2_code,
                    iso3_code = EXCLUDED.iso3_code,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        nationalities_added += result.rowcount

    for item in ETHNICITIES:
        result = await session.execute(
            text(
                """
                INSERT INTO ethnicities (code, name, normalized_name, bhxh_code, is_active)
                VALUES (:code, :name, :normalized_name, :bhxh_code, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    bhxh_code = EXCLUDED.bhxh_code,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        ethnicities_added += result.rowcount

    for item in RELIGIONS:
        result = await session.execute(
            text(
                """
                INSERT INTO religions (code, name, normalized_name, is_active)
                VALUES (:code, :name, :normalized_name, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        religions_added += result.rowcount

    for item in BANKS:
        result = await session.execute(
            text(
                """
                INSERT INTO banks (code, name, normalized_name, short_name, bin_code, swift_code, is_active)
                VALUES (:code, :name, :normalized_name, :short_name, :bin_code, :swift_code, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    short_name = EXCLUDED.short_name,
                    bin_code = EXCLUDED.bin_code,
                    swift_code = EXCLUDED.swift_code,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        banks_added += result.rowcount

    for item in LEAVE_TYPES:
        result = await session.execute(
            text(
                """
                INSERT INTO leave_types
                    (code, name, normalized_name, is_paid_leave, affects_annual_leave, allow_half_day,
                     requires_attachment, color_tag, is_active, description,
                     count_public_holidays, max_days_per_year, max_consecutive_days,
                     min_advance_days, carryover_allowed, carryover_cutoff_month)
                VALUES
                    (:code, :name, :normalized_name, :is_paid_leave, :affects_annual_leave, :allow_half_day,
                     :requires_attachment, :color_tag, true, :description,
                     :count_public_holidays, :max_days_per_year, :max_consecutive_days,
                     :min_advance_days, :carryover_allowed, :carryover_cutoff_month)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    is_paid_leave = EXCLUDED.is_paid_leave,
                    affects_annual_leave = EXCLUDED.affects_annual_leave,
                    allow_half_day = EXCLUDED.allow_half_day,
                    requires_attachment = EXCLUDED.requires_attachment,
                    color_tag = EXCLUDED.color_tag,
                    is_active = true,
                    description = EXCLUDED.description,
                    count_public_holidays = EXCLUDED.count_public_holidays,
                    max_days_per_year = EXCLUDED.max_days_per_year,
                    max_consecutive_days = EXCLUDED.max_consecutive_days,
                    min_advance_days = EXCLUDED.min_advance_days,
                    carryover_allowed = EXCLUDED.carryover_allowed,
                    carryover_cutoff_month = EXCLUDED.carryover_cutoff_month
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        leave_types_added += result.rowcount

    return (
        contract_categories_added,
        nationalities_added,
        ethnicities_added,
        religions_added,
        banks_added,
        leave_types_added,
    )


async def seed_sample_other_business_catalog(session: AsyncSession) -> tuple[int, int, int, int]:
    skills_added = 0
    certificates_added = 0
    templates_added = 0
    placeholders_added = 0

    for item in SKILLS:
        result = await session.execute(
            text(
                """
                INSERT INTO skills (code, name, normalized_name, skill_group, is_active)
                VALUES (:code, :name, :normalized_name, :skill_group, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    skill_group = EXCLUDED.skill_group,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        skills_added += result.rowcount

    for item in CERTIFICATES:
        result = await session.execute(
            text(
                """
                INSERT INTO certificates
                    (code, name, normalized_name, certificate_group, issuer_name, expiry_policy,
                     default_valid_months, is_active)
                VALUES
                    (:code, :name, :normalized_name, :certificate_group, :issuer_name, :expiry_policy,
                     :default_valid_months, true)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    certificate_group = EXCLUDED.certificate_group,
                    issuer_name = EXCLUDED.issuer_name,
                    expiry_policy = EXCLUDED.expiry_policy,
                    default_valid_months = EXCLUDED.default_valid_months,
                    is_active = true
                """
            ),
            {**item, "normalized_name": _normalize(item["name"])},
        )
        certificates_added += result.rowcount

    for item in CONTRACT_TEMPLATES:
        file_size, file_checksum = _template_file_meta(item["storage_path"])
        result = await session.execute(
            text(
                """
                INSERT INTO contract_templates
                    (code, name, normalized_name, contract_category_id, document_kind, template_engine,
                     file_name, storage_path, mime_type, file_size, file_checksum, version_no,
                     effective_from, effective_to, is_active, note)
                SELECT
                    :code, :name, :normalized_name, cc.id, :document_kind, :template_engine,
                    :file_name, :storage_path, :mime_type, :file_size, :file_checksum, :version_no,
                    NULL, NULL, true, :note
                FROM contract_categories cc
                WHERE cc.code = :contract_category_code
                ON CONFLICT (code, version_no) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    contract_category_id = EXCLUDED.contract_category_id,
                    document_kind = EXCLUDED.document_kind,
                    template_engine = EXCLUDED.template_engine,
                    file_name = EXCLUDED.file_name,
                    storage_path = EXCLUDED.storage_path,
                    mime_type = EXCLUDED.mime_type,
                    file_size = EXCLUDED.file_size,
                    file_checksum = EXCLUDED.file_checksum,
                    is_active = true,
                    note = EXCLUDED.note
                """
            ),
            {
                **item,
                "file_size": file_size,
                "file_checksum": file_checksum,
                "normalized_name": _normalize(item["name"]),
            },
        )
        templates_added += result.rowcount

    for template_code, rows in CONTRACT_TEMPLATE_PLACEHOLDERS.items():
        template_id = (
            await session.execute(
                text("SELECT id FROM contract_templates WHERE code = :code AND version_no = 1"),
                {"code": template_code},
            )
        ).scalar()
        if not template_id:
            continue

        await session.execute(
            text("DELETE FROM contract_template_placeholders WHERE template_id = :template_id"),
            {"template_id": template_id},
        )

        for row in rows:
            result = await session.execute(
                text(
                    """
                    INSERT INTO contract_template_placeholders
                        (template_id, placeholder_key, label, source_scope, source_path, data_type,
                         formatter, is_required, default_value, sort_order)
                    VALUES
                        (:template_id, :placeholder_key, :label, :source_scope, :source_path, :data_type,
                         :formatter, :is_required, :default_value, :sort_order)
                    ON CONFLICT (template_id, placeholder_key) DO UPDATE SET
                        label = EXCLUDED.label,
                        source_scope = EXCLUDED.source_scope,
                        source_path = EXCLUDED.source_path,
                        data_type = EXCLUDED.data_type,
                        formatter = EXCLUDED.formatter,
                        is_required = EXCLUDED.is_required,
                        default_value = EXCLUDED.default_value,
                        sort_order = EXCLUDED.sort_order
                    """
                ),
                {
                    "template_id": template_id,
                    "placeholder_key": row[0],
                    "label": row[1],
                    "source_scope": row[2],
                    "source_path": row[3],
                    "data_type": row[4],
                    "formatter": row[5],
                    "is_required": row[6],
                    "default_value": row[7],
                    "sort_order": row[8],
                },
            )
            placeholders_added += result.rowcount

    return skills_added, certificates_added, templates_added, placeholders_added
