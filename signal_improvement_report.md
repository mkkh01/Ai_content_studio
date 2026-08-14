# تقرير تحسين نموذج الإشارة

## نطاق التجربة

أُعيد الاختبار على بيانات BTCUSDT Futures الحقيقية من Binance Vision للفترة 2025-01-01 إلى 2026-07-31، بدقة ساعة، مع تنفيذ عند افتتاح الشمعة التالية، وخصم رسوم 6 نقاط أساس وانزلاق 4 نقاط أساس. أضيفت خصائص ديناميكية محسوبة من الماضي فقط لـ Open Interest وtaker imbalance وfunding، مع الاحتفاظ بخصائص المصدر الأصلية.

## مقارنة الآفاق في walk-forward

| المجموعة | الأفق | النموذج | متوسط Sharpe الصافي | وسيط Sharpe النسبي | متوسط العائد الصافي | متوسط التداولات |
|---|---:|---|---:|---:|---:|---:|
| baseline | 6h | HistGradientBoosting | -1.8256 | -2.6006 | -0.7383% | 11.63 |
| baseline | 12h | HistGradientBoosting | 0.6418 | 1.3337 | 0.8738% | 7.13 |
| baseline | 24h | HistGradientBoosting | -1.8393 | -2.0957 | -0.7567% | 4.38 |
| derivatives | 6h | HistGradientBoosting | -2.4304 | -1.2077 | -2.0926% | 10.88 |
| derivatives | 12h | HistGradientBoosting | -0.7609 | 0.2962 | -0.4944% | 8.75 |
| derivatives | 24h | HistGradientBoosting | 1.1706 | 0.8224 | -0.1525% | 4.00 |

تحسن الأفق 12 ساعة في baseline والأفق 24 ساعة في derivatives بعض مقاييس Sharpe، لكن العائد الصافي ظل سالبًا في derivatives عند 24 ساعة، كما بقي عدد التداولات منخفضًا. لذلك لا يكفي تحسن Sharpe النسبي منفردًا.

## حساسية تكلفة الأفق 24 ساعة

| التكلفة | النموذج | Sharpe النسبي المتوسط | العائد الصافي المتوسط | متوسط التداولات |
|---:|---|---:|---:|---:|
| 1× | HistGradientBoosting | -0.5011 | -0.1525% | 4.00 |
| 2× | HistGradientBoosting | -0.5990 | -0.2592% | 3.88 |
| 3× | HistGradientBoosting | -2.6156 | -1.0971% | 4.13 |

## الاختبار الخارجي الشهري

بعد إعادة الاختبار بالخصائص الجديدة، بقي العائد الخارجي غير مستقر. تحسنت بعض الأشهر، لكن عدة أشهر ظلت سالبة بقوة، ولا تحقق السلسلة شرط الإيجابية عبر ثلثي الأشهر أو عائدًا متوسطًا موجبًا.

## القرار

طبقت بوابة القبول دون تغيير معاييرها، وكانت النتيجة:

```text
FAIL_REMAIN_PAPER_TRADING
```

التحسينات مفيدة تشخيصيًا، خصوصًا اختبار الآفاق الأطول وإضافة التحولات الديناميكية، لكنها لم تثبت edge قابلًا للتداول بعد التكلفة. لم تُرقَّ أي نسخة إلى الإنتاج، ولم تُخفض عتبات البوابة لتجاوز الفشل.

## ملاحظة عن order-flow

المصدر التاريخي المتاح في ملف metrics يوفر taker long/short ratio كـ proxy في هذه التجربة، وليس دائمًا أحجام buyVol وsellVol الخام. لذلك لا يزال اختبار order-flow الخام الحقيقي خطوة مستقلة مطلوبة قبل استنتاج أن عائلة order-flow قد فشلت نهائيًا.

المصادر: [Binance Public Data](https://github.com/binance/binance-public-data)، [Binance Data Collection](https://data.binance.vision/)، [Binance Futures Market Data API](https://developers.binance.com/en/docs/derivatives/usds-margined-futures/market-data/rest-api).
