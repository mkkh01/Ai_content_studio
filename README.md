# Crypto Research Lab

نظام بحث وتجارب قابل لإعادة الإنتاج لبناء محرك تنبؤ لسوق العملات الرقمية الفوريّة. هذا الإصدار لا يدّعي امتلاك نموذج رابح مسبقًا؛ بل يوفّر دورة واضحة للبيانات، وهندسة الخصائص، وتوليد المرشحين، والتحقق الزمني، والاختبار الخلفي، وتسجيل النتائج.

## التشغيل

افتح `index.html` مباشرةً في المتصفح لعرض لوحة المختبر. ولتشغيل محرك التجارب الحقيقي على ملف OHLCV بصيغة CSV:

```bash
python3 research_engine.py --csv data/btcusdt_1h.csv --iterations 20 --output runs
```

يجب أن يحتوي CSV على `timestamp,open,high,low,close,volume`. يدعم المحرك أيضًا أعمدة اختيارية مثل `funding_rate` و`open_interest`.

## مبادئ السلامة البحثية

يستخدم المحرك تقسيمًا زمنيًا لا عشوائيًا، ويمنع استخدام بيانات المستقبل عند بناء الخصائص، ويحسب تكاليف التداول والانزلاق، ويفصل بين التدريب والتحقق والاختبار النهائي. النتائج البحثية ليست نصيحة مالية ولا ضمانًا للأداء.

## بنية النظام

| المكوّن | الوظيفة |
|---|---|
| `research_engine.py` | خط أنابيب قابل للتشغيل للتنظيف، والخصائص، وتوليد المرشحين، والتحقق المتدرج، والـ backtest، والسجل |
| `ml_walk_forward.py` | تطبيق Elastic Net وHistGradientBoosting مع walk-forward وSharpe صافيًا بعد التكلفة |
| `technical_hgb_compare.py` | مقارنة HistGradientBoosting قبل وبعد خصائص RSI وATR وMACD، مع النمط المصغر |
| `robust_evaluation.py` | تقييم 8 نوافذ walk-forward مع هدف صافي وحساسية 1x/2x/3x للتكلفة وخطوط أساس |
| `external_july_eval.py` | اختبار خارجي: تدريب/تحقق يناير–يونيو ثم اختبار يوليو دون إعادة ملاءمة |
| `derivatives_compare.py` | مقارنة HistGradientBoosting بين OHLCV وخصائص funding |
| `external_derivatives_eval.py` | اختبار funding خارجي على يوليو |
| `derivatives_report.md` | تقرير دمج funding وحساسية التكلفة |
| `binance_derivatives_loader.py` | تنزيل ودمج funding وOpen Interest وorder-flow مع backward as-of وprovenance زمني |
| `readiness_gate.py` | بوابة قبول مستقلة تمنع الإنتاج ما لم تجتز النتائج خارج العينة وحساسية التكلفة |
| `root_cause_decision_report.md` | تقرير التحقيق الجذري والقرار النهائي |
| `research_findings.md` | ملخص المراجع العلمية حول CPCV وDSR وتكاليف التنفيذ |
| `index.html` | لوحة مراقبة محلية تعرض حالة دورة البحث، المقاييس، النماذج، والسجلات |
| `lab.css` | تصميم الواجهة |
| `lab.js` | منطق الواجهة، محاكاة دورة بحث محلية، وتصدير النتائج |

يُفضّل تشغيل التجارب على بيانات محفوظة ومؤرخة مع نسخة مصدر واضحة، وحفظ مخرجات `runs/` مع كل تجربة. الإصدار الحالي يطبق نافذة تدريب فعلية، purge زمنيًا بمقدار أفق التنبؤ، validation منفصل لاختيار lambda، حذف الأهداف المستقبلية المفقودة بدل تحويلها إلى صفر، ومنطقة حياد مرتبطة بالتكلفة والتقلب. وتقيّم `score()` عوائد غير متداخلة فقط: عند أفق 24 ساعة تؤخذ ملاحظة مستقلة كل 24 شمعة، وتستخدم السنونة `bars_per_year / horizon`. كما يُسجل عدد الملاحظات ويُرفض النموذج إذا كان أقل من 20 ملاحظة مستقلة. تتضمن الخصائص الآن ATR وParkinson وGarman–Klass والتقلب المحقق ونسبة التقلب. كما يدعم التقييم وقفًا أوليًا ووقفًا متحركًا قائمًا على ATR، وحجم مركز متدرج حسب ATR، وtime stop، ووقف التعادل بعد حركة مواتية. ويسجل عدد الخروج بالوقف والخروج الزمني ووقف التعادل ومتوسط مدة الاحتفاظ وحجم المركز. ويستخدم الآن أربع نوافذ walk-forward ومعيار `composite_score` يجمع وسيط Sharpe وتذبذبه ومتوسط العائد مع عقوبة قلة التداولات؛ ولا يُقبل النموذج إلا إذا اجتاز النوافذ المتعددة واتساق الأداء وحدود العينة. أضيفت أيضًا خصائص اتجاه متعددة الأطر، EMA gap/slope، كفاءة الاتجاه، ADX تقريبي، درجات regime للتوجه الصاعد والهابط والجانبي والتقلب المرتفع، وتفاعلات regime مع الزخم والارتداد والتقلب. ويتيح `feature_mode` اختيار `baseline` أو `core_regime` أو `regime_interactions` أو `full` أو `derivatives`، إضافة إلى `return_path` و`reversion` و`liquidity` و`return_reversion` و`return_liquidity` و`alternative_full`. يضيف `derivatives` funding rate وتغيره ومجموعه المتحرك بعد دمج آمن زمنيًا من Binance Futures. تتضمن العائلات البديلة العائد المعياري واتساق المسار وموضع السعر مقابل VWAP ومقاييس السيولة والتكلفة. أظهرت دراسة الحذف أن `liquidity` هو أفضل مرشح نسبيًا، ولذلك أصبح الإعداد الافتراضي المؤقت هو `liquidity`، دون اعتبار ذلك اعتمادًا لاستراتيجية تداول. يوفّر `ml_walk_forward.py` نموذجَي Elastic Net وHistGradientBoosting، ويختار المعاملات داخل validation، ثم يحسب `sharpe_net` و`relative_sharpe` والعائد الصافي بعد الرسوم والانزلاق على نوافذ اختبار غير متداخلة. مثال التشغيل: `python3 ml_walk_forward.py --csv data/btcusdt.csv --output runs_ml --horizon 6 --windows 4`. أضيف نمط `technical` لاختبار RSI وATR وMACD، ونمط `minimal_technical` الذي يحتفظ فقط بـ RSI-14 وMACD histogram. لم تثبت التجارب الحالية تحسن أي منهما، لذلك لا يُستخدمان افتراضيًا. كما يطبق `ml_walk_forward.py` هدفًا تدريبيًا معدلًا بالتكلفة، وعتبة حياد تعتمد على عدم اليقين، ويفصل العائد الخام المستخدم في backtest عن هدف التدريب. ويستخدم التنفيذ عند افتتاح الشمعة التالية، مع purge بمقدار الأفق بين التدريب والتحقق والاختبار. يتيح `robust_evaluation.py` تشغيل 8 نوافذ walk-forward وحساسية تكاليف متعددة مع مقارنة عدم التداول وBuy-and-hold. ويتيح `external_july_eval.py` اختبارًا خارجيًا محفوظًا على يوليو بعد التدريب على يناير–يونيو. لم يثبت الإصلاح وجود نموذج قابل للتداول، ولذلك يظل الامتناع قرارًا صحيحًا عندما لا تتجاوز الإشارة التكلفة وعدم اليقين.

## دمج بيانات Funding وOpen Interest وOrder-Flow

يحتوي `binance_derivatives_loader.py` على مسار قابل لإعادة الإنتاج لتنزيل أرشيفات Binance Vision اليومية أو الشهرية وتوحيدها مع بيانات OHLCV. يستخدم المسار `merge_asof` باتجاه `backward`، ويحفظ أعمدة `source_timestamp_*` للمراجعة، ويرفض أي حالة يكون فيها توقيت المصدر بعد توقيت شمعة السوق. ويُسمح بمصدر قديم بحد أقصى يحدده `--tolerance`؛ والقيمة الافتراضية ثماني ساعات.

بالنسبة إلى Open Interest، تُقرأ أعمدة `sum_open_interest` و`sum_open_interest_value` من أرشيف `metrics`. وإذا احتوى المصدر على `sum_taker_long_short_vol_ratio`، يحتفظ به الكود كـ `taker_buy_sell_ratio` واضح الاسم باعتباره **proxy**، وليس حجم شراء أو بيع خام. ويمكن تمرير ملف order-flow منفصل يحوي `buyVol` و`sellVol` أو أسماء مكافئة عبر `--order-flow`، وعندها يحسب الكود `taker_imbalance`.

مثال تشغيل على بيانات تاريخية حقيقية:

```bash
python3 binance_derivatives_loader.py \\
  --bars /path/to/btcusdt_ohlcv.csv \\
  --output data/btcusdt_derivatives.csv \\
  --symbol BTCUSDT \\
  --start 2026-01-01 \\
  --end 2026-07-31 \\
  --cache-dir data/binance_cache \\
  --tolerance 8h
```

ولتمرير ملف order-flow تاريخي منفصل:

```bash
python3 binance_derivatives_loader.py \\
  --bars /path/to/btcusdt_ohlcv.csv \\
  --order-flow /path/to/taker_buy_sell.csv \\
  --output data/btcusdt_derivatives.csv \\
  --symbol BTCUSDT --start 2026-01-01 --end 2026-07-31
```

### بوابة الجهوزية

لا ينبغي اعتبار نجاح الدمج دليلًا على صلاحية استراتيجية. تفحص `readiness_gate.py` نتائج walk-forward وحساسية 1x و2x للتكلفة والاختبار الخارجي، وتعيد `FAIL_REMAIN_PAPER_TRADING` عند فشل أي شرط. لا تسمح البوابة بقبول نموذج من شهر واحد، أو من متوسط Sharpe مرتفع مع عائد صافٍ سلبي، أو من أداء لا يتحمل مضاعفة التكلفة.

```bash
python3 readiness_gate.py \\
  --walk-forward /path/to/derivatives_compare_summary.csv \\
  --cost-summary /path/to/derivatives_cost_summary.csv \\
  --external /path/to/external_derivatives_summary.csv \\
  --output runs/readiness_gate.json
```

لا ينبغي اعتبار نجاح الدمج دليلًا على صلاحية استراتيجية. يجب تشغيل `ml_walk_forward.py` و`robust_evaluation.py` على الناتج، مع تنفيذ T+1، وpurge، وتكاليف متعددة، واختبار خارجي منفصل. تعتمد بنية الأرشيفات على [Binance Public Data](https://github.com/binance/binance-public-data) و[Binance Data Collection](https://data.binance.vision/)، وتفاصيل الحقول الحية موثقة في [Binance Futures Market Data API](https://developers.binance.com/en/docs/derivatives/usds-margined-futures/market-data/rest-api).
