# تقرير بيانات المشتقات: Funding

## ما أضيف

أُضيفت بيانات Binance Futures funding rate من أرشيف Binance العام لشهور يناير–يوليو 2026. جرى دمج كل قيمة مع آخر funding معروف قبل الشمعة، باستخدام backward as-of، ثم اشتُقت `funding_change` و`funding_8h_sum`. لم تُستخدم أي قيمة مستقبلية.

أضيف نمط `feature_mode=derivatives` الذي يضيف خصائص funding إلى baseline دون إدخالها في baseline نفسه.

## النتائج الداخلية

على 8 نوافذ walk-forward، مع تنفيذ عند افتتاح الشمعة التالية، purge بمقدار أفق 6 ساعات، وتدريب 1,440 شمعة وvalidation/test قدرهما 240 شمعة، تحسن HistGradientBoosting عند إضافة funding:

| المجموعة | متوسط Sharpe الصافي | وسيط Sharpe النسبي | متوسط العائد الصافي | متوسط التداولات |
|---|---:|---:|---:|---:|
| baseline | −5.6982 | −4.7154 | −4.3241% | 14.38 |
| derivatives | **−3.0354** | **0.6312** | **−2.5187%** | 15.00 |

التحسن مهم تشخيصيًا لكنه لا يحقق معيار الترقية، لأن متوسط العائد وSharpe الصافي ما زالا سلبيين.

## اختبار خارجي على يوليو

تم التدريب والتحقق على يناير–يونيو فقط ثم الاختبار على يوليو:

| المجموعة | Sharpe الاختبار | Sharpe النسبي | العائد الصافي | التداولات |
|---|---:|---:|---:|---:|
| baseline | 1.9477 | 0.3442 | 0.6703% | 4 |
| derivatives | **2.9029** | **1.2994** | **2.5803%** | 11 |

هذه نتيجة مشجعة، لكنها لا تكفي للحكم؛ يوليو نافذة واحدة وكانت Buy-and-hold موجبة، كما أن عدد التداولات 11 فقط.

## حساسية التكلفة

| التكلفة | baseline Sharpe النسبي | derivatives Sharpe النسبي | derivatives العائد |
|---:|---:|---:|---:|
| 1× | −4.7154 | **0.6312** | −2.5187% |
| 2× | −7.8796 | **−1.5149** | −3.6155% |
| 3× | −6.1068 | −9.6811 | −5.6998% |

ينهار التحسن عند مضاعفة التكلفة، ولذلك لا يمكن اعتباره أفضلية اقتصادية ثابتة. هذا يتوافق مع ضرورة نمذجة spread وslippage والسيولة، لا رسوم ثابتة فقط [3].

## القرار

تم الاحتفاظ بـ `derivatives` كخيار تجريبي، ولم يُجعل إعدادًا افتراضيًا. لا تزال الحاجة قائمة إلى بيانات spread وorder-flow وopen interest تاريخية متزامنة. يجب اختبار funding على عدة أشهر خارج العينة، مع Deflated Sharpe وتصحيح تعدد التجارب قبل أي ترقية [2].

## المراجع

[1]: https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/ "Binance Futures funding archive"
[2]: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 "The Deflated Sharpe Ratio"
[3]: https://www.quantstart.com/articles/Successful-Backtesting-of-Algorithmic-Trading-Strategies-Part-II/ "Successful Backtesting: transaction costs and implementation issues"
