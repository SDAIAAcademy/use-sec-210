# المختبرات: USE-SEC-210

ستة عشر مختبرًا على جدول بيانات (LibreOffice Calc أو Excel أو Google Sheets): ثمانية من 25 دقيقة (1.2 و1.3 و1.6 و1.8 و2.2 و2.5 و2.6 و2.8) وثمانية من 20 دقيقة (1.1 و1.4 و1.5 و1.7 و2.1 و2.3 و2.4 و2.7)، أي ست ساعات في المجموع.
كل مختبر يبدأ من ملفات جاهزة في `files/`، فلا يحتاج نتيجة مختبر سابق. لا مختبر يستدعي نموذجًا لغويًّا.

| المختبر | الصفحة | ملفات البداية |
|---|---|---|
| 1.1 سلاسل القرار | `D1_1_decision_chains.html` | `use_cases.csv`، `chain_template.csv`، `prework_sheet.csv` |
| 1.2 خط الأساس الموسمي | `D1_2_seasonal_baseline.html` | `retail/sales_weekly.csv` |
| 1.3 الخطأ والتكلفة بحسب المجموعة | `D1_3_error_by_group.html` | `start/forecast_errors_y2.csv`، `retail/cost_by_group.csv`، `retail/vendor_offer.txt` |
| 1.4 العروض والنفاد | `D1_4_promo_and_stockouts.html` | `start/forecast_errors_y2.csv` |
| 1.5 التقييم دون اتصال | `D1_5_offline_vs_popular.html` | `retail/reco_offline.csv`، `retail/reco_vendor_note.txt` |
| 1.6 قراءة تجربة A/B | `D1_6_ab_readout.html` | `retail/ab_test_daily.csv`، `retail/ab_vendor_readout.txt`، `notebooks/ab_readout.ipynb` |
| 1.7 جرد الموافقات | `D1_7_consent_inventory.html` | `pricing/` |
| 1.8 الفروق بين الفئات | `D1_8_group_differences.html` | `start/offers_with_groups.csv` |
| 2.1 قراءة تجربة الاحتفاظ | `D2_1_read_the_trial.html` | `telecom/retention_trial.csv`، `telecom/trial_note.txt` |
| 2.2 جدول الأثر الإضافي | `D2_2_uplift_table.html` | `telecom/retention_trial.csv` |
| 2.3 قيمة ثلاث سياسات | `D2_3_policy_value.html` | `start/uplift_cells.csv` |
| 2.4 الادعاء الصادق | `D2_4_honest_claim.html` | `telecom/campaign_months.csv`، `telecom/campaign_report.txt` |
| 2.5 مطابقة التنبيهات | `D2_5_alert_matching.html` | `network/alerts_week.csv`، `network/incidents_week.csv`، `network/rasd_note.txt` |
| 2.6 العتبة | `D2_6_threshold.html` | `start/alert_matches.csv`، `start/incident_best_score.csv`، `network/noc_capacity.txt` |
| 2.7 سُبات وطلب الموقع | `D2_7_energy_and_location.html` | `network/energy_pilot.csv`، `network/subat_vendor_claim.txt`، `network/location_request.txt` |
| 2.8 خريطة الفرص والمخاطر | `D2_8_opportunity_map.html` | `map/use_cases.csv`، `map/scoring_guide.txt`، `map/map_template.csv` |

## الحلول

- `solutions/check.py` يعيد حساب كل مختبر من ملفات المشارك بالطريقة التي تطلبها الصفحة، ويقارن بـ`solutions/key.json`.
  مكتبة Python القياسية فقط، ولا يكتب شيئًا على القرص:

  ```
  uv run labs/solutions/check.py          # النتيجة المتوقعة: 16 of 16 labs pass
  uv run labs/solutions/check.py 2.6      # مختبر واحد
  ```

- `solutions/answer_key.md` المفتاح للمدرّب: ما زُرع في كل مختبر، والأرقام المتوقعة، والفخ الأشيع.
- قسم «للمدرّب» في آخر صفحة كل مختبر فيه المفتاح نفسه.

## البيانات

كل الملفات اصطناعية، يكتبها `_tools/prepare_files.py` (مكتبة Python القياسية، البذرة 210) مع نصوص الحالة في
`_tools/case_texts.py`. إعادة التوليد تعطي الملفات نفسها بايتًا ببايت:

```
uv run labs/_tools/prepare_files.py
```

تنبؤ «استشراف» في `retail/sales_weekly.csv` ملاءمة حقيقية بالمربعات الصغرى على السنة الأولى. كل مخرجات
الأنظمة الأخرى («مختارات» و«سعرك» و«بقاء» و«رصد» و«سُبات») مولّدة بقواعد معلنة في المولّد، لا من نماذج مدرّبة.

## الدفتر

`notebooks/ab_readout.ipynb` يكمل المختبر 1.6 لمن يريد: يقرأ `retail/ab_test_daily.csv` ويحسب الارتفاع وفترة
الثقة ونسبة التوزيع لكل أسبوع، بمكتبة Python القياسية فقط. يعمل في Colab أو JupyterLite أو أي Jupyter محلي،
ويُحفظ دون مخرجات؛ وحين يُشغَّل تطابق أرقامه `key.json`. المختبر نفسه يُحل بجدول البيانات دون الدفتر.
