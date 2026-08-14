# نتائج المراجعة العلمية

## المصادر

1. Arian, Mobarekheh, Seco, *Backtest overfitting in the machine learning era: A comparison of out-of-sample testing methods in a synthetic controlled environment*, Knowledge-Based Systems, 2024. URL: https://www.sciencedirect.com/science/article/pii/S0950705124011110
2. Bailey and López de Prado, *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*, Journal of Portfolio Management, 2014. URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

## النقاط ذات الصلة

تذكر دراسة ScienceDirect أن البيانات المالية غير ثابتة، ذات ارتباط ذاتي وتحولات نظامية، وأنها تقارن طرق K-Fold وPurged K-Fold وCombinatorial Purged Cross-Validation. وتعرض CPCV كطريقة مرتبطة بانخفاض Probability of Backtest Overfitting وارتفاع Deflated Sharpe مقارنة ببعض الطرق التقليدية، مع التنبيه إلى أن اختيار طريقة التحقق يؤثر في متانة بيانات التدريب.

يوضح Bailey وLópez de Prado أن اختبار عدد كبير من الاستراتيجيات أو المعاملات يسبب تضخمًا في النتائج بسبب selection bias وbacktest overfitting. ويهدف Deflated Sharpe Ratio إلى تصحيح تضخم Sharpe الناتج عن تعدد الاختبارات وعدم طبيعية العوائد، للتمييز بين النتيجة التجريبية الحقيقية والصدفة الإحصائية.

## انعكاس مبدئي على المشروع

المشروع اختبر أعدادًا كبيرة من مجموعات الخصائص والنماذج، واستخدم عددًا محدودًا من النوافذ. لذلك لا يكفي اختيار أفضل composite من النتائج الحالية. يجب تسجيل عدد التجارب الكامل، حساب تصحيح لتعدد الاختبارات، إبقاء اختبار خارجي لم يُستخدم مطلقًا، وتطبيق purge/embargo على أي labels متداخلة قبل الاختيار.

3. QuantStart, *Successful Backtesting of Algorithmic Trading Strategies - Part II*. URL: https://www.quantstart.com/articles/Successful-Backtesting-of-Algorithmic-Trading-Strategies-Part-II/

يشرح المصدر أن تكاليف backtest لا تقتصر على الرسوم، بل تشمل slippage/latency وmarket impact والسيولة والـspread. كما يحذر من أن التكلفة الثابتة قد تسيء تقدير الكلفة الفعلية، وأن الاستراتيجيات عالية التواتر حساسة للتنفيذ. ويشير إلى أن بيانات OHLC المركبة قد تحتوي قيمًا متطرفة لا تمثل قابلية التنفيذ في البورصة المستهدفة.

4. López de Prado, *Advances in Financial Machine Learning* / CPCV reference. URL: https://www.quantresearch.org/Innovations.htm
5. Springer, *A Bayesian-based classification framework for financial time series trend prediction*, 2023. URL: https://link.springer.com/article/10.1007/s11227-022-04834-4

تدعم هذه المصادر استخدام purging لإزالة عينات labels المتداخلة وembargo لمعالجة الارتباط التسلسلي بعد حدود الاختبار. المصدر العلمي يذكر أن labels المتداخلة تسبب تسربًا، وأن embargo يعالج الاعتماد بين الخصائص حول حدود التقسيم.

## استنتاج بحثي مبدئي

المشروع الحالي لديه ثلاثة مخاطر منهجية مستقلة: (1) القرار مبني على close ثم يُقيّم كأنه قابل للتنفيذ عند close دون تأخير، (2) اختيار النموذج لا يطبق purge/embargo كاملًا في وحدة ML، و(3) البيانات لا تحتوي spread/order-flow حقيقيًا، لذلك التكلفة الثابتة لا تمثل التنفيذ. التدقيق الداخلي وجد أن momentum الاتجاهي الساذج كان سلبيًا عند الآفاق 1 و3 و6 و12 ساعة، ولم تظهر علاقة موجبة مستقرة في OHLCV وحده. هذا يرجح أن الحل الجذري هو إصلاح بروتوكول التنفيذ والهدف والتقييم، ثم اختبار ما إذا كانت البيانات تحمل إشارة أصلًا، لا إضافة مؤشرات فنية جديدة.
