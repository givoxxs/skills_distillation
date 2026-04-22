# SkillsBench Tasks

Local copy of [SkillsBench](https://github.com/benchflow-ai/skillsbench) tasks for reference in the distillation pipeline.

**80 tasks · ~260MB · Copied from `skillsbench/tasks/`**

---

## Cấu trúc mỗi task

```
<task-name>/
├── instruction.md          # Đề bài cho agent (human-written, outcome-focused)
├── task.toml               # Metadata: category, difficulty, timeout, resource limits
├── environment/
│   ├── Dockerfile          # Docker container setup
│   ├── <input files>       # Fixture data (xlsx, pdf, pptx, pcap, video...)
│   └── skills/             # SKILL.md files inject vào agent
│       └── <skill-name>/
│           └── SKILL.md
├── solution/
│   └── solve.sh            # Oracle solution (human-written, must pass 100%)
└── tests/
    ├── test.sh             # Pytest runner → ghi reward.txt (0 hoặc 1)
    └── test_outputs.py     # Pytest assertions kiểm tra output
```

**Scoring:** Binary — tất cả tests pass → `reward = 1`, bất kỳ test fail → `reward = 0`.

---

## Tổng quan

| | |
|---|---|
| Tổng tasks | 80 |
| Difficulty easy | 9 |
| Difficulty medium | 48 |
| Difficulty hard | 23 |
| Skills liên quan docx/xlsx/pptx/pdf | 10 tasks |

---

## Tasks liên quan nhất đến pipeline (docx / xlsx / pptx / pdf)

| Task | Skills | Tests | Diff | Mô tả ngắn |
|---|---|---|---|---|
| `weighted-gdp-calc` | xlsx | 27 | medium | INDEX/MATCH + SUMPRODUCT tính weighted mean GCC GDP |
| `pptx-reference-formatting` | pptx | 12 | medium | Format dangling paper titles, tạo reference slide |
| `pdf-excel-diff` | pdf, xlsx | 11 | medium | So sánh employee records giữa PDF backup và Excel |
| `powerlifting-coef-calc` | xlsx, pdf, senior-data-scientist | 11 | easy | Tính IPF scoring coefficients từ competition data |
| `sales-pivot-analysis` | pdf, xlsx | 10 | medium | Pivot analysis từ population PDF + income Excel |
| `exceltable-in-ppt` | pptx, xlsx | 8 | medium | Update embedded Excel table trong PPTX, giữ formula |
| `xlsx-recover-data` | xlsx, data-reconciliation | 8 | medium | Recover 15 missing values (`???`) qua cross-sheet deps |
| `shock-analysis-supply` | xlsx | 9 | hard | Cobb-Douglas macro model, investment shock estimation |
| `offer-letter-generator` | docx | 4 | easy | Fill template Word với split placeholders + conditionals |
| `organize-messy-files` | docx, pptx, pdf, file-organizer | 6 | medium | Phân loại 100+ PDF/PPTX/DOCX vào 5 thư mục theo topic |

---

## Tất cả 83 tasks

### Financial Analysis & Excel

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `weighted-gdp-calc` | xlsx | 27 | medium | 224K | Tính weighted mean net exports %GDP cho 6 nước GCC bằng INDEX/MATCH + SUMPRODUCT trong gdp.xlsx |
| `xlsx-recover-data` | xlsx, data-reconciliation | 8 | medium | 104K | Recover 15 missing values (`???`) trong nasa_budget_incomplete.xlsx bằng cách phân tích cross-sheet dependencies |
| `reserves-at-risk-calc` | xlsx | 5 | medium | 320K | Download IMF commodity database, tính reserves-at-risk metrics |
| `shock-analysis-demand` | xlsx | 5 | medium | 172K | Ước lượng investment spending shock cho Georgia (macro model) |
| `shock-analysis-supply` | xlsx | 9 | hard | 212K | Tương tự demand nhưng dùng Cobb-Douglas production function |
| `financial-modeling-qa` | pdf, xlsx | 4 | hard | 716K | QA trên large-scale financial data file |
| `invoice-fraud-detection` | fuzzy-match, pdf, xlsx | 2 | hard | 264K | Phát hiện gian lận invoice bằng fuzzy matching giữa PDF và Excel |
| `sales-pivot-analysis` | pdf, xlsx | 10 | medium | 324K | Pivot analysis kết hợp population PDF + income Excel |
| `pdf-excel-diff` | pdf, xlsx | 11 | medium | 160K | Extract employee table từ PDF, so sánh với Excel, output diff JSON |
| `powerlifting-coef-calc` | powerlifting, senior-data-scientist, xlsx | 11 | easy | 148K | Tính IPF Wilks/Dots coefficients cho powerlifting competitions |
| `protein-expression-analysis` | xlsx | 6 | medium | 176K | Phân tích protein expression data từ cancer cell line experiments |

### Office Suite (PPTX / DOCX)

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `offer-letter-generator` | docx | 4 | easy | 88K | Fill offer letter template Word với split placeholders, nested tables, conditional sections |
| `pptx-reference-formatting` | pptx | 12 | medium | 1.6M | Detect dangling titles trong PPTX, format font/color/size, tạo reference slide |
| `exceltable-in-ppt` | pptx, xlsx | 8 | medium | 1.4M | Update embedded Excel table trong PPTX, preserve formula cells |
| `organize-messy-files` | docx, file-organizer, pdf, planning-with-files, pptx | 6 | medium | 36M | Phân loại 100+ PDF/PPTX/DOCX vào 5 thư mục: LLM, quantum, black hole, DNA, music |
| `court-form-filling` | pdf | 5 | easy | 432K | Fill California Small Claims Court form PDF từ case description |

### Security & CVE

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `dapt-intrusion-detection` | pcap-analysis, threat-detection | 14 | hard | 31M | Phân tích PCAP traffic, compute stats, điền values vào JSON |
| `fix-druid-loophole-cve` | jackson-security, senior-java | 4 | hard | 316K | Patch CVE trong Apache Druid 0.20.0 (Jackson deserialization) |
| `fix-erlang-ssh-cve` | erlang-concurrency, erlang-distribution, erlang-otp-behaviors, find-bugs, senior-security, ssh-penetration-testing | 3 | hard | 160K | Fix critical SSH vulnerability trong Erlang/OTP |
| `suricata-custom-exfil` | pcap-triage-tshark, suricata-offline-evejson, suricata-rules-basics | 12 | medium | 80K | Viết Suricata rules phát hiện data exfiltration trong HTTP traffic |
| `syzkaller-ppdev-syzlang` | syz-extract-constants, syzkaller-build-loop, syzlang-ioctl-basics | 7 | medium | 56K | Viết syzkaller syzlang cho Linux parallel port driver (ppdev) |
| `software-dependency-audit` | cvss-score-extraction, trivy-offline-vulnerability-scanning, vulnerability-csv-reporting | 4 | medium | 632K | Security audit dependency file, extract CVE scores, output CSV |
| `setup-fuzzing-py` | discover-important-function, fuzzing-python, setup-env | 0 | medium | 96K | Setup continuous fuzzing cho Python libraries |

### Control Systems & Engineering

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `adaptive-cruise-control` | csv-processing, pid-controller, simulation-metrics, vehicle-dynamics, yaml-config | 12 | medium | 116K | Implement ACC simulation với PID controller, maintain 30m/s |
| `hvac-control` | excitation-signal-design, first-order-model-fitting, imc-tuning-rules, safety-interlocks, scipy-curve-fit | 7 | medium | 92K | Implement temperature controller, maintain 22°C |
| `r2r-mpc-control` | finite-horizon-lqr, integral-action-design, mpc-horizon-tuning, state-space-linearization | 6 | medium | 72K | Implement MPC controller cho 6-section Roll-to-Roll manufacturing line |
| `3d-scan-calc` | mesh-analysis | 2 | hard | 68K | Tính mass của 3D printed part từ STL binary scan data |

### Energy & Power Systems

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `energy-ac-optimal-power-flow` | ac-branch-pi-model, casadi-ipopt-nlp, power-flow-data | 24 | medium | 244K | Tạo base case AC optimal power flow cho peak load ngày mai |
| `energy-market-pricing` | dc-power-flow, economic-dispatch, locational-marginal-prices, power-flow-data | 4 | hard | 1.4M | Phân tích market pricing anomaly, tính locational marginal prices |
| `grid-dispatch-operator` | dc-power-flow, economic-dispatch, power-flow-data | 6 | medium | 1.4M | Tối ưu generator dispatch cho power network snapshot |

### Manufacturing

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `manufacturing-codebook-normalization` | manufacturing-failure-reason-codebook-normalization | 16 | medium | 2.6M | Normalize defect reason codes từ free-text của engineers |
| `manufacturing-equipment-maintenance` | reflow-profile-compliance-toolkit, reflow_machine_maintenance_guidance | 7 | medium | 3.1M | Maintenance guidance cho reflow machine theo manual |
| `manufacturing-fjsp-optimization` | fjsp-baseline-repair-with-downtime-and-policy | 15 | medium | 84K | Flexible Job Shop Scheduling với machine downtime constraints |

### Seismology & Astronomy

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `earthquake-phase-association` | gamma-phase-associator, obspy-data-api, seisbench-model-api, seismic-picker-selection | 1 | hard | 28M | Phase association từ earthquake traces (wave.mseed) |
| `earthquake-plate-calculation` | geospatial-analysis | 8 | medium | 1.7M | Tính plate tectonic parameters từ earthquake catalog |
| `seismic-phase-picking` | obspy-data-api, obspy-datacenter-client, seisbench-model-api, seismic-picker-selection | 2 | hard | 10M | Phase picking trên 100 earthquake traces |
| `gravitational-wave-detection` | conditioning, matched-filtering | 9 | medium | 3.9M | Detect gravitational wave signal từ binary black hole merger trong noisy data |
| `exoplanet-detection-period` | box-least-squares, exoplanet-workflows, light-curve-preprocessing, lomb-scargle-periodogram, transit-least-squares | 4 | medium | 824K | Detect orbital period của exoplanet từ TESS lightcurve |

### ML / AI Research

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `mhc-layer-impl` | mhc-algorithm, modal-gpu, nanogpt-training | 23 | hard | 188K | Implement Multi-Head Compression layer cho nanoGPT (DeepSeek-inspired) |
| `taxonomy-tree-merge` | hierarchical-taxonomy-clustering | 24 | hard | 3.6M | Merge product category taxonomies từ Amazon, Facebook, Google |
| `trend-anomaly-causal-inference` | data_cleaning, did_causal_analysis, feature_engineering, time_series_anomaly_detection | 15 | hard | 212K | Causal inference (DiD) trên e-commerce transaction data |
| `simpo-code-reproduction` | nlp-research-repo-package-installment, pdf | 1 | hard | 5.8M | Reproduce SimPO loss function từ NLP paper |
| `glm-lake-mendota` | glm-basics, glm-calibration, glm-output | 3 | hard | 7.4M | Run General Lake Model, simulate water temperature cho Lake Mendota |
| `jax-computing-basics` | jax-skills | 5 | medium | 116K | Solve set of programming tasks bằng JAX |
| `lean4-proof` | lean4-memories, lean4-theorem-proving | 4 | medium | 616K | Complete Lean 4 theorem proofs từ template |

### Web / Frontend

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `fix-visual-stability` | browser-testing, react-best-practices, web-interface-guidelines | 6 | hard | 476K | Fix layout shift issues trong Next.js e-commerce app |
| `react-performance-debugging` | browser-testing, react-best-practices | 11 | hard | 540K | Debug và fix performance issues trong slow Next.js app |
| `data-to-d3` | d3-visualization | 10 | medium | 2.5M | Visualize stock data bằng D3.js v6 |

### PDF / Document Processing

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `edit-pdf` | pdf-editing, text-parser | 9 | medium | 192K | Edit PDF theo instructions từ text file |
| `latex-formula-extraction` | marker, pdf | 7 | medium | 396K | Extract tất cả LaTeX formulas từ research paper PDF |
| `paper-anonymizer` | academic-pdf-redaction, pdf | 6 | medium | 7.4M | Anonymize 3 research papers PDF (redact tên tác giả, affiliation) |
| `flink-query` | pdf, senior-data-engineer | 3 | hard | 1.9M | Implement Flink streaming job từ skeleton code + dataset |
| `find-topk-similiar-chemicals` | pdf, pubchem-database, rdkit | 1 | medium | 392K | Tìm top-K similar chemicals trong molecules.pdf qua PubChem |
| `citation-check` | citation-management | 9 | medium | 312K | Verify bibliography integrity của research paper trước khi submit |

### Video / Audio / Multimodal

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `multilingual-video-dubbing` | ffmpeg-audio-processing, ffmpeg-format-conversion, ffmpeg-media-info, ffmpeg-video-editing, ffmpeg-video-filters, text-to-speech | 8 | medium | 432K | Dub video sang ngôn ngữ khác trong time window chỉ định |
| `speaker-diarization-subtitles` | automatic-speech-recognition, multimodal-fusion, speaker-clustering, voice-activity-detection | 10 | hard | 5.2M | Diarization + subtitle generation cho audio/video |
| `video-filler-word-remover` | ffmpeg-video-editing, filler-word-processing, whisper-transcription | 5 | medium | 12M | Detect và remove filler words (um, uh...) từ interview video |
| `mario-coin-counting` | ffmpeg, image_editing, object_counter | 3 | medium | 15M | Đếm coins trong Super Mario gameplay video |
| `pedestrian-traffic-counting` | gemini-count-in-video, gemini-video-understanding, gpt-multimodal, video-frame-extraction | 1 | hard | 25M | Đếm pedestrian từ surveillance camera videos |
| `pg-essay-to-audiobook` | audiobook, elevenlabs-tts, gtts, openai-tts | 4 | medium | 68K | Convert Paul Graham essays thành audiobook |
| `dynamic-object-aware-egomotion` | dyn-object-masks, egomotion-estimation, output-validation, sampling-and-indexing | 10 | medium | 1.1M | Phân tích camera motion + dynamic object detection từ video |

### 3D Graphics

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `threejs-structure-parser` | obj-exporter, threejs | 3 | medium | 96K | Parse Three.js code, hiểu structure của complex scene |
| `threejs-to-obj` | obj-exporter, threejs | 3 | medium | 76K | Convert Three.js scene thành OBJ format |

### Software Engineering

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `spring-boot-jakarta-migration` | hibernate-upgrade, jakarta-namespace, restclient-migration, spring-boot-migration, spring-security-6 | 10 | hard | 196K | Migrate legacy Spring Boot app lên Jakarta EE namespace |
| `fix-build-agentops` | analyze-ci, temporal-python-testing, testing-python, uv-package-manager | 3 | easy | 152K | Fix build errors trong Python codebase (CI failures) |
| `fix-build-google-auto` | maven-build-lifecycle, maven-dependency-management, maven-plugin-configuration | 3 | easy | 92K | Fix Maven build errors trong Java codebase |
| `parallel-tfidf-search` | memory-optimization, python-parallelization, workload-balancing | 5 | medium | 140K | Optimize TF-IDF search engine bằng parallelization |
| `gh-repo-analytics` | gh-cli | 8 | medium | 48K | Viết "December community pulse" report cho cli/cli GitHub repo |
| `react-performance-debugging` | browser-testing, react-best-practices | 11 | hard | 540K | Debug performance issues trong Next.js app |

### Science & Research

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `quantum-numerical-simulation` | qutip | 7 | medium | 104K | Simulate open Dicke model steady state, tính Wigner function |
| `econ-detrending-correlation` | timeseries-detrending | 4 | medium | 156K | Detrend economic time series, tính business cycle correlation |
| `lake-warming-attribution` | contribution-analysis, meteorology-driver-classification, pca-decomposition, trend-analysis | 2 | medium | 64K | Attribution analysis cho lake warming trend |
| `flood-risk-analysis` | flood-detection, nws-flood-thresholds, usgs-data-download | 2 | medium | 48K | Tìm USGS stations bị flooding trong April 1-7, 2025 |
| `lab-unit-harmonization` | lab-unit-harmonization | 8 | medium | 1.3M | Harmonize clinical lab data từ nhiều sources khác nhau |

### Healthcare

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `lab-unit-harmonization` | lab-unit-harmonization | 8 | medium | 1.3M | Harmonize đơn vị đo lường trong clinical lab data |

### Games / Simulation

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `civ6-adjacency-optimizer` | civ6lib, hex-grid-spatial, map-optimization-strategy, sqlite-map-parser | 10 | hard | 592K | Tối ưu district adjacency bonuses trong Civilization 6 |
| `dialogue-parser` | dialogue_graph | 6 | easy | 172K | Convert text dialogue thành structured JSON graph |
| `virtualhome-agent-planning` | pddl-skills | 2 | medium | 10M | Solve planning tasks bằng PDDL (VirtualHome environment) |
| `pddl-tpp-planning` | pddl-skills | 2 | medium | 348K | Solve Travelling Purchase Problem bằng PDDL |

### Networking / DevOps

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `azure-bgp-oscillation-route-leak` | azure-bgp | 4 | medium | 224K | Detect BGP route oscillation và leaks trong Azure Virtual WAN |
| `scheduling-email-assistant` | constraint-parser, gmail-skill, google-calendar-skill | 2 | medium | 260K | Đọc meeting request emails, reply và schedule vào Google Calendar |
| `enterprise-information-search` | enterprise-artifact-search | 3 | hard | 26M | Retrieve information từ enterprise data file |

### Chemistry / Materials

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `find-topk-similiar-chemicals` | pdf, pubchem-database, rdkit | 1 | medium | 392K | Tìm top-K similar chemicals qua PubChem + RDKit |

### Misc

| Task | Skills | Tests | Diff | Size | Mô tả |
|---|---|---|---|---|---|
| `jpg-ocr-stat` | image-ocr, openai-vision, pdf, video-frame-extraction, xlsx | 1 | hard | 8.1M | OCR scanned receipt images, tính statistics, output Excel |

---

---

## Phân tích task đặc biệt

### `shock-analysis-supply` — tại sao `hard`?

Task yêu cầu agent xây dựng một **macro-economics model hoàn chỉnh trong Excel** để ước lượng tác động của khoản đầu tư $6.5 tỷ USD vào nền kinh tế Georgia qua 8 năm (2026–2033). Ba bước liên tiếp, phụ thuộc nhau:

**Bước 1 — Thu thập data từ 3 nguồn live internet**
Agent phải tự crawl web bằng Playwright MCP, không có data sẵn trong fixture:
- **PWT** (Penn World Tables, `rug.nl`) — capital stock, employment của Georgia
- **IMF WEO** — real GDP 2000–2027, tự extend công thức đến 2043
- **ECB** — Consumption of Fixed Capital để tính depreciation rate

**Bước 2 — HP Filter trong Excel bằng Solver**
Dùng Hodrick-Prescott filter (phương pháp kinh tế lượng) để tách trend khỏi cycle:
- Viết công thức `LnK`, `LnY`, `LnZ` trong các cột
- Setup **Excel Solver** tối thiểu hóa objective function tại cell `P5` bằng cách thay đổi 22 cells `L6:L27`
- Solver là add-in của Excel — phải kích hoạt và cấu hình đúng

**Bước 3 — Cobb-Douglas Production Function**
```
Ystar = A × K^α × L^(1-α)
```
- Extend LnZ trend đến 2041 bằng hàm `TREND`
- Tính `Ystar_base` (không đầu tư) và `Ystar_with` (có đầu tư $6.5B)
- Capital accumulation: `K_t = K_{t-1} × (1 − δ) + I_t` dùng depreciation rate từ sheet CFC

**9 tests kiểm tra:**

| Test | Kiểm tra |
|---|---|
| `test_required_sheets_exist` | 5 sheets: PWT, WEO_Data, CFC data, Production, Investment |
| `test_data_collection` | Column B&C trong PWT có data, CFC có depreciation formulas |
| `test_weo_data_extended_with_formulas` | ≥10 formula cells cho năm 2028–2043 |
| `test_production_depreciation_rate` | B3 là formula, giá trị 0 < δ < 0.3 |
| `test_hp_filter_setup` | LnK/LnY có LN formulas, P5 có objective, L6:L27 có values |
| `test_production_function_calculations` | EXP formulas cho Ystar, TREND formula có mặt |
| `test_investment_and_capital_accumulation` | Link tới Investment sheet, dùng `$B$3` trong capital formulas |
| `test_ky_ratio_and_k_extension` | Division formulas K/Y, AVERAGE formula |
| `test_value_magnitudes` | δ ∈ (0.01, 0.03), Ystar ∈ (10k, 500k), GDP 2028 ∈ (70, 120) |

**Hard vì 3 lý do cộng dồn:**
1. **Domain knowledge sâu** — phải hiểu macro-economics (Cobb-Douglas, HP filter, depreciation) để biết điền đúng cell nào
2. **Multi-source data collection live** từ internet, không deterministic, web có thể thay đổi structure
3. **Excel Solver** — tối ưu hóa trong Excel add-in, không thể hardcode, phải để Excel tự chạy solver

---

## Skills index (unique skills có trong skillsbench_tasks)

Các skills xuất hiện ≥ 2 tasks:

| Skill | Tasks dùng |
|---|---|
| `xlsx` | 13 |
| `pdf` | 12 |
| `pptx` | 3 |
| `power-flow-data` | 3 |
| `browser-testing` | 2 |
| `dc-power-flow` | 2 |
| `docx` | 2 |
| `economic-dispatch` | 2 |
| `ffmpeg-video-editing` | 2 |
| `obj-exporter` | 2 |
| `obspy-data-api` | 2 |
| `pddl-skills` | 2 |
| `react-best-practices` | 2 |
| `seisbench-model-api` | 2 |
| `seismic-picker-selection` | 2 |
| `threejs` | 2 |
| `video-frame-extraction` | 2 |

---

## Notes

- Đây là **bản copy tĩnh** — không tự cập nhật khi SkillsBench upstream thay đổi.
- 5 tasks lớn nhất đã bị xóa để tiết kiệm dung lượng: `sec-financial-report` (164M), `mars-clouds-clustering` (47M), `video-tutorial-indexer` (35M), `travel-planning` (32M), `video-silence-remover` (31M).
- 3 tasks có **0 test cases** đã bị xóa: `crystallographic-wyckoff-position-analysis`, `python-scala-translation`, `setup-fuzzing-py`.
- Thư mục này được `.gitignore` — không commit lên repo.
