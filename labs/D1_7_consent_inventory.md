---
course: "الذكاء الاصطناعي في التجزئة والاتصالات"
code: "USE-SEC-210"
version: "2027.1.0"
lab: "1.7"
language: "ar"
view: "trainee"
source: "https://sdaiaacademy.github.io/use-sec-210/labs/D1_7_consent_inventory.html"
---

# المختبر 1.7 · جرد مدخلات سعرك أمام الموافقات

تجرد مدخلات قاعدة «سعرك» وتربط كل مدخل بغرض الموافقة الذي يحتاجه، ثم تعدّ في قسائم الشهر العملاء الذين استُعملت بياناتهم دون الموافقة المطلوبة.

اليوم 1 · الجلسة 7: الأسعار المخصصة والموافقة

### ستخرج من هذا المختبر بـ

- جدول مدخلات قاعدة «سعرك»: لكل مدخل الغرض الذي يخدمه والموافقة التي يحتاجها.
- عدد القسائم التي استعملت كل مدخل دون موافقته، من قسائم شهر كامل.
- الفجوات الثلاث الأكبر، مكتوبة لمسؤولة حماية البيانات.

## ما تحتاجه

[**pricing/saerak_rule.txt**وصف القاعدة كما سلّمه المورد](https://sdaiaacademy.github.io/use-sec-210/labs/files/pricing/saerak_rule.txt) [**pricing/consent_purposes.txt**أغراض الموافقة الثلاثة في التطبيق](https://sdaiaacademy.github.io/use-sec-210/labs/files/pricing/consent_purposes.txt) [**pricing/customers.csv**6,000 عميل وأعلام موافقاتهم](https://sdaiaacademy.github.io/use-sec-210/labs/files/pricing/customers.csv) [**pricing/offers_month.csv**قسائم الشهر والمدخلات التي استعملها كل منها](https://sdaiaacademy.github.io/use-sec-210/labs/files/pricing/offers_month.csv)

الأداة جدول بيانات. سياسة الذكاء الاصطناعي: مساعد معلّم. لا يحتاج المختبر شيئًا من مختبر سابق. البيانات اصطناعية، والجدول تمرين على الأسئلة لا رأي قانوني.

## الخطوات

### 1 · اقرأ القاعدة والأغراض 3 دقائق

اقرأ **saerak_rule.txt** و**consent_purposes.txt**. علّم في وصف القاعدة كل نوع من البيانات تقرؤه، وكل جملة عن من تُطبَّق عليه القاعدة.

### 2 · جدول المدخلات 5 دقائق

| المدخل | عمود الاستعمال في القسائم | الغرض الذي يخدمه | الموافقة التي يحتاجها |
| --- | --- | --- | --- |
| سجل المشتريات | `used_purchase_history` |  |  |
| الموقع | `used_location` |  |  |
| نوع الجهاز | `used_device` |  |  |
| الدفع بالتقسيط | `used_instalments` |  |  |
| العمر | `used_age` |  |  |
| شريحة الاهتمام الصحي | `health_segment_offer` |  |  |
| إرسال القسيمة نفسها | كل القسائم |  |  |

### 3 · اربط القسائم بالعملاء 3 دقائق

الملفان مرتبان برقم العميل، صفًّا مقابل صف. انسخ أعمدة الموافقة الثلاثة من **customers.csv** إلى يسار القسائم، ثم تحقق:

```
# ملف: offers_month.csv
J2  =customers!F2      consent_marketing
K2  =customers!G2      consent_personalisation
L2  =customers!H2      consent_location
M2  =A2=customers!A2   same customer? must be TRUE on every row
```

### 4 · عدّ القسائم دون موافقة 6 دقائق

```
# ملف: offers_month.csv
history without personalisation  =COUNTIFS(D:D,1,K:K,0)
location without location        =COUNTIFS(E:E,1,L:L,0)
no marketing consent at all      =COUNTIF(J:J,0)
health segment offers            =COUNTIF(I:I,1)
```

واسأل عن الجهاز والتقسيط والعمر: أي غرض موافقة يغطي استعمالها لتحديد السعر؟

### 5 · الفجوات الثلاث 3 دقائق

اكتب لوصال الحبشان ثلاث فجوات مرتبة بخطورتها، لكل منها: المدخل، وعدد العملاء، وما يجب أن يتوقف أو يتغير أولًا.

### ✱ تمرين إضافي

عدّ قسائم الشهر التي لا فجوة فيها: صاحبها وافق على التسويق والتخصيص، ولم يُستعمل موقعه إلا بموافقته، وليست من الشريحة الصحية. ماذا يقول الرقم عن حجم القاعدة بعد إصلاحها؟

## أسئلة تحقق

1. لماذا لا تغطي موافقة التسويق استعمال سجل المشتريات في تحديد السعر؟
2. ما الذي يجعل شريحة الاهتمام الصحي أخطر من غيرها؟
3. القرار يصدر دون مراجعة أحد: ماذا يغيّر ذلك في نوع الموافقة المطلوبة؟
