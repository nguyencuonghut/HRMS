........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 16%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 33%]
........................................................................ [ 38%]
........................................................................ [ 44%]
........................................................................ [ 49%]
........................................................................ [ 55%]
........................................................................ [ 60%]
........................................................................ [ 66%]
........................................................................ [ 71%]
........................................................................ [ 77%]
........................................................................ [ 82%]
.................................................s.......s.............. [ 88%]
........................................................................ [ 93%]
........................................................................ [ 99%]
...........                                                              [100%]
=============================== warnings summary ===============================
../usr/local/lib/python3.12/site-packages/fastapi/testclient.py:1
  /usr/local/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_bhxh_salary_adjustments.py::TestValidation::test_employee_without_profile_returns_422
  /app/app/api/v1/endpoints/salary.py:85: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = await salary_service.create_bhxh_adjustment(session, body, current_user.id)

tests/test_certificates.py::TestCertificateCRUD::test_create_expiry_before_issued_returns_422
  /usr/local/lib/python3.12/site-packages/fastapi/routing.py:328: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    return await dependant.call(**values)

tests/test_contract_generation.py::test_generate_contract_no_template_file_422
  /app/app/api/v1/endpoints/employee_contracts.py:182: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    docx_bytes, filename = await generate_contract_document(

tests/test_insurance_changes.py::TestManualChangeEvents::test_create_event_invalid_reason_type_mismatch
  /app/app/api/v1/endpoints/insurance.py:258: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    return await insurance_change_service.create_manual_event(

tests/test_insurance_changes.py: 22 warnings
tests/test_insurance_reports.py: 2 warnings
  /usr/local/lib/python3.12/site-packages/openpyxl/worksheet/_reader.py:329: UserWarning: Data Validation extension is not supported and will be removed
    warn(msg)

tests/test_insurance_reports.py::TestReportCreation::test_create_supplement_requires_initial_to_exist
  /app/app/api/v1/endpoints/insurance.py:298: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    return await insurance_report_service.create_report(session, body, current_user.id)

tests/test_insurance_reports.py::TestApprovalWorkflow::test_cannot_submit_empty_report
  /app/app/api/v1/endpoints/insurance.py:335: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    return await insurance_report_service.submit_for_review(session, report_id, current_user.id)

tests/test_insurance_reports.py::TestExport::test_export_draft_report_returns_422
tests/test_insurance_reports.py::TestExport::test_export_pending_report_returns_422
  /app/app/api/v1/endpoints/insurance.py:406: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    buf, filename = await insurance_export_service.export_d02_ts_from_report(session, report_id)

tests/test_kpi_monthly.py::TestKpiImport::test_import_non_xlsx_returns_422
  /app/app/api/v1/endpoints/performance.py:100: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = await kpi_service.import_kpi_excel(session, content, current_user.id)

tests/test_recruitment_candidates.py::TestCandidateApplication::test_apply_draft_jr_returns_422
  /app/app/api/v1/endpoints/recruitment.py:1029: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = await candidate_service.apply_candidate(session, candidate_id, data, current_user.id)

tests/test_recruitment_posting.py::TestPostingCreate::test_create_posting_from_draft_jr_fails_422
tests/test_recruitment_posting.py::TestPostingCreate::test_create_with_past_deadline_fails_422
  /app/app/api/v1/endpoints/recruitment.py:616: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = await job_posting_service.create_posting(session, body, current_user.id)

tests/test_recruitment_posting.py::TestPostingCreate::test_create_with_invalid_channel_fails_422
  /app/app/services/job_posting_service.py:222: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    await _validate_channels(session, data.channels)

tests/test_salary_summary.py::TestGetSalarySummary::test_returns_empty_when_no_active_employees_for_month
  /app/app/services/salary_service.py:853: DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    rates, _ = await _get_rates_for_month(session, year, month)

../usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:475
  /usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:475: PytestCacheWarning: cache could not write path /app/.pytest_cache/v/cache/nodeids: [Errno 13] Permission denied: '/app/.pytest_cache/v/cache/nodeids'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

../usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:429
  /usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:429: PytestCacheWarning: cache could not write path /app/.pytest_cache/v/cache/lastfailed: [Errno 13] Permission denied: '/app/.pytest_cache/v/cache/lastfailed'
    config.cache.set("cache/lastfailed", self.lastfailed)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.13-final-0 _______________

Name                                             Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------------------------
app/api/v1/deps.py                                  48     11     16      5    69%   30, 38-40, 47, 67-71, 86-92
app/api/v1/endpoints/admin_units.py                 59      9      0      0    85%   62, 81, 95, 116, 145, 154, 175, 187, 200
app/api/v1/endpoints/audit_logs.py                  58      3     14      1    94%   93-94, 114
app/api/v1/endpoints/auth.py                       157     45     32      6    67%   78->85, 80->85, 82-83, 90, 105, 112-113, 119-122, 133-144, 170, 173, 178-179, 182-199, 208-209, 213, 237-239, 254-261, 270-282, 312
app/api/v1/endpoints/bhyt_clinic.py                 52     34     14      0    27%   30-42, 51-58, 68-77, 86-90
app/api/v1/endpoints/contract_reports.py            29      4      2      0    81%   112-116
app/api/v1/endpoints/data_imports.py                35      3      2      0    92%   25-27
app/api/v1/endpoints/departments.py                 35      2      0      0    94%   27, 43
app/api/v1/endpoints/disciplines.py                 41     10      4      0    69%   136, 153-162
app/api/v1/endpoints/education_catalog.py          108     35      0      0    68%   57, 70, 79, 91, 93, 107, 117-132, 165, 184, 193, 204-235, 247, 260, 273, 291, 304, 324-341, 353, 366
app/api/v1/endpoints/employee_contracts.py          71     23      2      0    66%   53, 59, 81-83, 89, 100, 105, 161-165, 185, 191, 205-216
app/api/v1/endpoints/employee_io.py                 44     12      0      0    73%   30-32, 101-106, 126-130
app/api/v1/endpoints/employees.py                  330    105      4      0    67%   104, 136, 138-145, 163, 171, 183-185, 187, 200-204, 206-208, 216, 228, 248, 263, 270, 301, 308, 323-331, 346, 385, 391, 407, 413, 430, 436, 468-469, 476, 493, 500, 516, 554, 560, 577, 583, 599, 619-620, 636, 638, 645, 662, 669, 685, 705-706, 723, 729, 746, 752, 766-773, 788-789, 806, 812, 829, 835, 849-856, 871-872, 890, 897, 914, 921, 935-942, 1014-1015, 1034-1036, 1082, 1114-1118, 1136-1140, 1159, 1172-1177, 1192-1197
app/api/v1/endpoints/export.py                      45      5      0      0    89%   35, 64-65, 79, 116
app/api/v1/endpoints/hr_reports.py                  32      2      0      0    94%   100, 109
app/api/v1/endpoints/insurance.py                   96      7      0      0    93%   287, 317, 326, 364, 374, 397, 407
app/api/v1/endpoints/job_positions.py               54      7      0      0    87%   132, 169-171, 188-189, 191
app/api/v1/endpoints/leave_entitlements.py          49     11      0      0    78%   51-59, 94-95, 109, 130-131, 139, 150-151
app/api/v1/endpoints/leave_records.py               46     13      0      0    72%   55, 64, 76-84, 97-105, 118-126, 138-139
app/api/v1/endpoints/notifications.py               91     38     28      2    50%   40, 52-54, 67-78, 81, 94-97, 108, 121-130, 133, 159-160, 162-163, 166, 171, 195-197
app/api/v1/endpoints/onboarding.py                  85     33      2      0    60%   53-55, 67-71, 86-87, 130-134, 144-145, 157-160, 172-176, 192-193, 195-199
app/api/v1/endpoints/org_history.py                 29      1      6      0    97%   53
app/api/v1/endpoints/other_business_catalog.py     314    143      2      0    54%   113-123, 128, 139-152, 162-167, 190-196, 204-205, 215-224, 233-240, 283-284, 287, 292, 300, 302-303, 306, 311-316, 329, 334-339, 344, 349-356, 361-366, 380, 385-390, 395, 400-407, 412-417, 439, 450, 456, 466, 486-487, 490, 495, 500, 505-512, 517-522, 527, 541-542, 550, 619-623, 638, 643, 648, 653, 658, 668
app/api/v1/endpoints/performance.py                 77      6      0      0    92%   85, 149, 225, 256, 291, 309
app/api/v1/endpoints/probation.py                  110     55     14      0    44%   43-44, 60-61, 93-104, 147-151, 169-174, 201-202, 212-215, 218-220, 234-265, 295-296, 306-309, 312-316
app/api/v1/endpoints/probation_reports.py           21      3      2      0    78%   59-64
app/api/v1/endpoints/recruitment.py                494    119      2      0    76%   160, 176, 182, 198, 204, 219, 289, 295, 311, 317, 332, 355, 361, 376, 382, 398, 404, 420, 426, 461, 479, 528, 545, 581, 618, 632, 647-649, 664, 670, 685, 691, 706, 712, 773, 778, 798, 803, 813, 837, 854, 889, 904-906, 920-921, 941, 995-997, 1010-1011, 1030, 1036, 1107, 1119, 1128-1129, 1150, 1161-1163, 1173-1174, 1186, 1198, 1223-1225, 1240-1242, 1271, 1289, 1299-1301, 1312, 1322-1324, 1337, 1348-1350, 1375, 1387, 1418, 1428-1430, 1439-1440, 1471, 1480, 1492, 1503, 1514, 1526, 1538, 1558, 1567, 1577-1579, 1598-1600, 1615, 1630-1636, 1711, 1723, 1744, 1765, 1774
app/api/v1/endpoints/rewards.py                     61     12      2      0    78%   57, 62, 75, 80, 92, 248, 261-266
app/api/v1/endpoints/roles.py                       76     31      8      0    54%   24-26, 47-52, 64-65, 68, 75-77, 90-92, 105-107, 116-118, 130-137, 151, 166, 172
app/api/v1/endpoints/salary.py                      32      1      0      0    97%   87
app/api/v1/endpoints/training.py                   157     26     10      1    79%   98, 104, 135, 141, 157, 204, 240, 261, 281, 302, 342, 351-354, 372, 379-382, 399, 456, 487, 518, 521, 722
app/api/v1/endpoints/users.py                      106     38     18      2    56%   35, 41, 59-61, 63-66, 78-79, 82, 89, 102, 116, 118-125, 133, 148-153, 170-171, 176, 201-202, 209, 216, 228-229, 231-232
app/core/cache.py                                   38     11      6      0    75%   40-42, 53-54, 58-61, 70-71
app/core/circuit_breaker.py                         60     14     10      3    70%   65, 83-84, 91-95, 103, 116-125, 128, 131-132
app/core/config.py                                 101     15     26      7    75%   64-70, 75, 86, 114-120, 124->129, 171, 176-179
app/core/database.py                                27      3      4      2    84%   38, 43-44
app/core/encryption.py                              43      5     12      3    85%   17, 30, 43-44, 49
app/core/rate_limit.py                              10      6      4      0    29%   7-12
app/core/storage.py                                136     23     12      4    82%   43, 48, 62, 67, 124-125, 141-142, 150-151, 164, 180-181, 193-194, 206-207, 219-220, 232-233, 241-242
app/middleware/csrf.py                              34     14     10      1    57%   45-50, 78-105
app/middleware/security_headers.py                  19      1      2      1    90%   97
app/models/bhyt_clinic.py                           13      2      0      0    85%   8-9
app/models/employee_education.py                    65      1      0      0    98%   11
app/models/employee_job.py                          25      1      0      0    96%   11
app/models/employee_relative.py                     20      1      0      0    95%   11
app/models/export.py                                42      1      0      0    98%   17
app/models/leave_entitlement.py                     22      1      0      0    95%   12
app/models/mixins.py                                13      1      0      0    92%   47
app/models/notification.py                          45      1      0      0    98%   12
app/models/performance.py                           31      1      0      0    97%   13
app/models/salary.py                                40      1      0      0    98%   11
app/models/salary_adjustment.py                     22      1      0      0    95%   13
app/models/training.py                              76      1      0      0    99%   13
app/schemas/catalog.py                             729     27      4      2    96%   143, 150, 238, 243, 289, 334, 339, 355, 393, 398, 410, 415, 447, 452, 462, 492, 497, 507, 563, 597, 602, 613, 648, 653, 667, 740, 820
app/schemas/department.py                           71      2      4      2    95%   52, 78
app/schemas/employee.py                            414      1      0      0    99%   189
app/schemas/employee_contract.py                    84      2     16      2    96%   28, 67
app/schemas/employee_insurance.py                  105      1     10      2    97%   69->74, 73
app/schemas/export.py                               70      1      4      2    96%   35->39, 38
app/schemas/insurance.py                            78      3      6      3    93%   49, 65, 68
app/schemas/insurance_report.py                     78      2      4      2    95%   93, 109
app/schemas/leave_record.py                         70      1     10      1    98%   24
app/schemas/recruitment.py                         892      4     14      5    99%   90->92, 503, 583, 707, 798
app/schemas/salary.py                              123      1      2      1    98%   70
app/schemas/training.py                            237      4     20      4    97%   206, 242, 244, 336
app/schemas/user.py                                 89      2     10      2    96%   27, 33
app/scripts/send_backup_notification.py             27     27      4      0     0%   1-54
app/services/administrative_import_service.py      183     11     36      6    92%   75, 95, 103, 138, 465, 587, 632-636
app/services/administrative_unit_service.py        198     69     84     22    58%   50, 64->66, 66->68, 68->70, 71, 73-74, 83, 102, 108, 110-111, 134, 144-161, 166, 173->176, 177, 179, 181, 183, 185, 191, 199, 206, 211, 219-221, 232-236, 276->278, 279-288, 296-307, 312-313, 341->346, 359->361, 363, 365, 375->377, 388-389, 396-401, 420-422, 448-458
app/services/auth_service.py                        82      9     14      1    85%   48, 55-59, 107, 123, 134
app/services/backup_notification_service.py         66      8     18      4    86%   28, 45, 48-49, 105, 109, 134-135
app/services/bhxh_export_service.py                118     71     18      1    40%   85, 90-130, 168-227
app/services/candidate_import_service.py           170     84     58      6    44%   49-91, 108-113, 119-123, 209-215, 225-227, 237-238, 245-247, 267-270, 278-316, 318-340, 342-344
app/services/candidate_service.py                  384    176    132     17    49%   70-72, 76, 93, 95, 101, 122-123, 131-135, 137-138, 141-144, 170->175, 172->175, 206, 224, 227, 239, 287, 295, 302, 307, 314, 323-335, 337-360, 441, 456, 463-468, 470-475, 483, 490-512, 538, 543, 547->550, 551, 559-574, 603-619, 627-628, 640-652, 654, 662-663, 665-673, 675, 681-683, 694-695, 697, 712-719, 732-737, 748-749, 760-769, 771, 777-779, 795-798, 810-816, 834-843, 859, 862, 869, 872, 883, 885, 892, 895, 903-904, 918, 920-927
app/services/certificate_service.py                167     71     66      6    48%   41-43, 66, 68-70, 123, 127, 135, 137, 141->144, 167-168, 171-172, 175, 190-193, 195-210, 213-221, 245-279, 298-303, 308-310, 315-317
app/services/contract_export_service.py             99     72     42      5    23%   59, 63, 65, 70-71, 80, 87, 91-205
app/services/contract_generate_service.py          175     69     88     14    56%   40, 48-50, 59, 66, 75, 78-87, 106, 107->109, 112, 115, 125-127, 139-141, 147, 166, 183-188, 199-207, 213-219, 259-265, 271-296, 299-301
app/services/contract_import_service.py            176     52     52      9    70%   114-117, 123, 132, 135-136, 138, 145, 153-155, 160, 167, 176, 210, 212, 227-230, 239-242, 245-257, 263-281, 283-292, 295
app/services/contract_report_service.py            135     71     36      5    42%   111, 121-171, 182-186, 241, 247, 268-269, 274, 277-309, 337, 346, 351-384, 393-413, 452-473, 488-489, 493, 505-529
app/services/contract_template_docx.py              93      3     36      8    91%   220, 253->251, 271->273, 274, 275->277, 278->280, 282->284, 310
app/services/dashboard_service.py                  145     72     50      4    42%   70, 81, 105-125, 130-151, 156-177, 182-184, 228-230, 233-252, 255-257, 259, 266-271, 278, 317-320, 325-348, 353-367, 393-409, 416-423, 442-454, 461-468
app/services/department_service.py                 120     68     44      1    34%   55-66, 79-82, 96, 99, 109-130, 142-168, 171, 185-235, 253-255, 265-277
app/services/discipline_service.py                 159     73     58      4    46%   45-47, 58, 65, 67-69, 99, 105, 141, 171-172, 176, 181, 191-220, 223, 243-285, 292-297, 305-308
app/services/document_checklist_service.py         278    161     84      7    35%   91, 119-120, 122-124, 145, 157-180, 182, 193-227, 236-239, 253-273, 285-288, 290, 319, 321-322, 326-333, 339, 353-416, 435->437, 439->441, 441->443, 467-544, 559-591, 601-624, 638, 650-656
app/services/education_catalog_service.py          238    110     94     33    46%   27->29, 28, 29->31, 30, 31->exit, 32, 45, 47-51, 52->exit, 53, 66, 68-72, 73->exit, 74, 80, 87, 94, 108, 110-111, 121-122, 126, 132-139, 141, 152-159, 161, 165-169, 175-176, 198, 199->201, 202, 203->212, 214->217, 220, 226-236, 238, 242-263, 271, 285, 287, 310-331, 337-344, 346, 350-365, 373, 386
app/services/employee_attachment_service.py         24      5      4      0    75%   42, 51-53, 77
app/services/employee_code_rule_service.py          88     40     18      0    49%   35, 43-48, 79-82, 94-109, 114, 120-123, 125, 131-134, 146-161, 166, 172-175, 177
app/services/employee_code_service.py               62     21     22      3    57%   60-61, 64->99, 81-88, 92-97, 107, 115, 134, 147-148, 150-152, 169
app/services/employee_contract_service.py          161     86     50      6    40%   69-71, 76-78, 84, 86, 98, 102, 104-114, 120-124, 133, 135-137, 148-149, 155, 157-160, 166-184, 188, 199-222, 227, 232-236, 240, 253-258, 262, 271-282, 314, 318, 320, 334-335, 338, 340-350
app/services/employee_education_service.py         141     60     28      0    48%   46-47, 49-52, 54-56, 118-120, 130-132, 140, 155, 180-182, 192-195, 202, 209, 246-256, 265-267, 277-279, 286-287, 294, 346-348, 358-360, 367-368, 383, 397-408, 415-417, 427-430, 436-437
app/services/employee_export_service.py            139     87     52      1    30%   41->44, 81-96, 101-107, 109-111, 113-114, 118-158, 165-166, 168-180, 186-211, 213, 216-232, 234-249, 251-265, 267-269, 271-287
app/services/employee_import_service.py            235     71     84     10    65%   151-152, 164-168, 170-173, 179-184, 194, 198->201, 202-205, 207-210, 218, 228-231, 235-238, 246-248, 253, 262, 268, 315, 317, 319, 340-343, 346, 350-367, 394-401, 403-404
app/services/employee_insurance_service.py         248    108     88     13    51%   73, 126, 138, 147, 156, 246, 266-268, 316, 324, 329, 333, 338, 343-351, 353-361, 365-375, 377-387, 392-395, 402-408, 416, 425-432, 438-441, 446-447, 451, 457-495, 504, 507-508, 523-526, 528-529, 531, 552, 556, 562-564, 567, 603-604, 607-619, 621-640, 649, 661-662, 665-675, 680-681
app/services/employee_job_service.py               111     56     32      1    39%   23-25, 29-32, 37-39, 51-55, 58-65, 82, 93, 109, 117, 130, 142, 178-179, 191-207, 209-211, 225-230, 238-249, 263-264, 276-279, 283-294
app/services/employee_relative_service.py           30      9      4      0    62%   31, 58-60, 70-73, 80
app/services/employee_service.py                   239     80    100     14    60%   41, 54-56, 61-63, 74->75, 77->78, 79-94, 112, 126, 132, 147, 167, 172, 187-190, 193, 243, 289-290, 315-322, 329, 331, 345-347, 355-359, 368, 393, 407-418, 429, 437, 440-456, 465-480, 487-489
app/services/export_service.py                     385     97     84     19    69%   84, 86, 96, 98, 108, 119, 121, 186, 189, 197, 239, 251, 263-282, 319-320, 324, 328-329, 333, 337-342, 346-364, 368-374, 378, 387-394, 398, 465, 495, 498-501, 505, 511, 526, 533-544, 547, 551-564, 567, 571, 576, 585-587, 592-596, 602-604, 612-614, 623, 625-628, 633, 636-638, 647, 659-661, 673, 732->735, 754
app/services/headcount_plan_service.py              86     36     28      4    49%   28-30, 63->65, 66, 71-72, 76, 80-81, 91-92, 94->95, 96-97, 106-121, 123, 133-141, 149, 151-156, 167, 172-180, 183-185
app/services/hiring_decision_service.py            171     97     70      2    37%   42-49, 51, 54, 86-90, 97-98, 104-105, 112-115, 128-131, 139-140, 147-165, 176-193, 211-219, 225-235, 266-271, 278-281, 298-301, 314-332, 338-343, 349-358, 365-373, 375-377, 383, 393, 395
app/services/hr_report_service.py                  294     83    126     30    66%   66-69, 75, 77-84, 90, 92-99, 105-108, 126, 161, 163, 229, 233-236, 238, 240, 243, 248, 250, 303, 305, 325->344, 327, 352->350, 363->361, 378->380, 383->381, 448->436, 493->497, 495, 499, 543->546, 550, 640-675, 683-710, 718-767
app/services/insurance_analytics_service.py        163    103     44      4    32%   54-63, 75-93, 106-136, 151, 182, 195-213, 237, 250-299, 339, 346, 353, 356-375, 420-436, 451-454, 459-462, 465-476, 504-506, 511, 517-585
app/services/insurance_change_service.py           150     68     50      4    50%   75, 77, 82-86, 101, 108, 120, 123, 131, 148, 154, 160-162, 165-168, 170-214, 216, 225-226, 233-248, 260-262, 269-272, 274-319, 322, 349, 360-362, 381-384, 398-405
app/services/insurance_export_service.py           114     42     26      2    54%   38, 44, 148-153, 159-187, 201-204, 228-233, 239-272
app/services/insurance_import_service.py           179     51     50      8    69%   98, 111, 119, 122-123, 125, 130, 137, 145-147, 152, 159, 168, 181, 185, 214-225, 227-233, 235-245, 247-260, 262-267, 270
app/services/insurance_policy_service.py           175     95     62      1    35%   45-52, 65, 84, 89-91, 101-102, 104-105, 107, 130, 138-139, 142-153, 156-157, 175-193, 195, 199-204, 213-214, 220, 234-242, 244-256, 264-270, 281-282, 293, 306-317, 334-345, 356-357, 371, 401-416
app/services/insurance_report_service.py           197    118     40      0    37%   39, 122, 130-155, 162-164, 185, 206-207, 224-241, 245, 265-266, 281-282, 293-317, 338, 341, 347-349, 357-364, 368-375, 383-434, 445, 448-459, 465, 473-481, 485-504, 516-517, 532-540, 545, 555-566, 579, 589-600, 613
app/services/interview_service.py                  272    155     96      9    35%   50, 56-58, 78->81, 86, 116-117, 119-137, 140-144, 147-148, 150-151, 158-159, 165, 170-171, 179-211, 216, 224-226, 228, 240-241, 249-260, 262, 271-276, 281-282, 286-298, 311, 320-325, 334, 343-344, 354->363, 364, 365->367, 368-370, 372-383, 402, 404, 423-428, 430-432, 434, 449-451, 461, 470-471, 480->489, 489->491, 494-496, 498-507, 524, 526, 542-554, 569-573
app/services/job_position_service.py               109     51     34      8    45%   51-52, 57-58, 71, 83, 92-95, 129, 156-157, 160, 163-174, 177, 180, 190-194, 196, 197->202, 198, 203-221, 224, 233->238, 234, 239-249, 252, 266, 280-283
app/services/job_posting_service.py                162     96     58      0    32%   50, 61-65, 67, 74-77, 79, 84-85, 93-98, 111-115, 129-130, 137, 140, 179-199, 203-206, 214-217, 224-247, 255-275, 283-291, 295-297, 305-315, 322-335, 353-364
app/services/job_title_service.py                   77     26     16      0    59%   59-62, 79, 93-100, 117-129, 148-160
app/services/jr_service.py                         191    101     60      4    38%   43-45, 115-118, 122-124, 146, 148, 150, 152-153, 163-164, 168, 182-183, 186-189, 191-199, 202-219, 221, 231-259, 266-271, 283-293, 304-313, 325-334, 346-356, 366, 372-385, 388, 402-410, 412, 431-439, 441, 455-457
app/services/kpi_service.py                        198     96     54      6    46%   36-38, 59, 61-63, 107, 131-136, 139-140, 143, 157-158, 169-185, 197-203, 210, 233-236, 240-241, 243-258, 260-321, 333-336, 346-353
app/services/leave_analytics_service.py            198     72     62      7    61%   37, 63, 76, 81-88, 101-116, 131-132, 149-177, 180-191, 226, 242-254, 293-316, 366, 368, 372, 375-392, 432, 436, 439-459, 518-526, 537
app/services/leave_entitlement_service.py          150     68     54      7    47%   64-66, 91-92, 106-108, 119-121, 154, 156-157, 170, 177, 179-183, 196->198, 197, 198->202, 199, 209-227, 239-248, 255-260, 276-285, 288-306, 315, 326-347, 350
app/services/leave_record_import_service.py        160     45     44     11    71%   93, 97-100, 106, 114, 117-118, 120, 125, 141, 149-151, 156, 163, 173, 192, 194, 209-212, 215-218, 222-240, 242-251, 256-260
app/services/leave_record_service.py               166     90     60      8    39%   35-36, 88, 93-95, 136, 142, 144, 146-147, 148->151, 159, 168-174, 178-180, 184, 190-199, 203-204, 213-214, 216-224, 227-255, 267-280, 286-295, 297-312, 323-326, 328-336, 344, 346-351
app/services/leave_report_service.py               150     34     46      7    76%   32-33, 85, 89-90, 98, 105, 108-130, 181, 183, 190-205, 244, 249, 256, 259-279, 324->326
app/services/link_service.py                        94     51     32      0    34%   31-33, 45-48, 54, 59-77, 86, 93-94, 96, 108-109, 112-117, 123-147, 161-162, 165-201
app/services/notification_service.py               139     39     40     13    65%   65->67, 67->69, 97, 110-150, 154-160, 176, 223, 233-262, 284->324, 287->324, 302-304, 324->362, 327->362, 341-343, 362->393, 393->430, 396->430, 410-412
app/services/offer_service.py                      141     77     40      1    36%   54, 65, 69-79, 129-132, 142-145, 157-181, 193-202, 209-215, 218-219, 221-222, 229-238, 242-244, 248-249, 251-252, 264-274, 277-280, 284-285, 287-288, 300-309
app/services/onboarding_service.py                 219    133     92      3    31%   62, 71, 76-88, 91, 100-106, 109, 116-117, 126-132, 150-153, 164, 170-175, 181-182, 194-230, 260-261, 271-283, 296-303, 318-319, 326-335, 346-354, 370-376, 380-383, 396-411, 426-437, 486, 489-490, 497-499, 503-505, 513-524, 528-533, 537-564, 569-597
app/services/other_business_catalog_service.py     384    176    110     23    48%   58->60, 59, 60->exit, 61, 77, 91->93, 95, 119->121, 127-129, 147, 149, 163-186, 190-213, 217-221, 225-228, 242, 256-259, 261, 278-284, 286, 294, 298, 306, 310, 314, 318, 322, 326, 330, 334, 338, 342, 346, 350, 354, 358, 362, 366, 376-377, 388, 390-391, 395, 407, 411-423, 427, 431-434, 438, 442, 446, 452, 457, 461-466, 470, 474, 478, 482-485, 520, 536, 546, 553, 554->exit, 555, 570, 572, 588-606, 608, 612-627, 631-635, 649, 657-658, 693-728, 749, 754-770
app/services/performance_export_service.py         126     80     22      1    36%   64-129, 133-166
app/services/performance_report_service.py          61     27     20      1    51%   42-47, 54-69, 116-127, 138, 158, 163-173
app/services/pipeline_service.py                   295    179    100      6    30%   56, 60, 64, 72-74, 79-81, 86-88, 93-95, 105, 122-123, 147-149, 151, 153-160, 181->184, 218-225, 227-236, 238, 245, 263-264, 275-281, 285-286, 288-289, 295-297, 307, 324-325, 336-337, 345-350, 357-371, 372->376, 373-375, 378-379, 390-393, 403-441, 445-472, 484-485, 487, 497, 511-512, 514-517, 527, 538-551, 555-557, 559-563, 565-572, 586-587, 596-597, 600-601, 603-604, 619-622, 631-632, 634-637, 647-648, 666
app/services/probation_report_service.py           199    129     72      4    33%   75, 78-120, 128, 147-232, 270, 275, 279-287, 289-302, 333, 341-424, 458-462, 464-465, 469-479, 512-518, 544-605
app/services/probation_service.py                  270    163     94      5    32%   100->101, 119-131, 133-147, 155-163, 180-184, 197-203, 205-207, 209-215, 221-222, 231-235, 245-275, 316-355, 375-401, 415-418, 431-432, 443-470, 473, 479, 489-503, 513, 536-546, 566-593, 597, 599, 601, 615-631, 642-660, 679-689, 709, 719-730, 733
app/services/recruitment_email_service.py          374    164    134     18    46%   105, 111-123, 128, 131-133, 152->157, 154->157, 161->164, 186, 188, 192-194, 200-215, 217, 221-230, 232, 236-240, 272->280, 275->280, 282->334, 286-287, 289-291, 293-304, 311-319, 326-332, 334->342, 337->342, 354-368, 379, 384-385, 389->392, 392->394, 411, 415, 423-444, 447-450, 452-456, 465, 476-477, 479, 485-493, 511-533, 550-551, 554-557, 559-562, 571-572, 590-597, 599-602, 611-612, 642-649, 651-654, 663-664, 682-689, 691-694, 703-704
app/services/recruitment_report_service.py         247    139     72      3    42%   46, 64-81, 92, 95, 98, 107, 116, 135-136, 155-156, 167-169, 179-184, 226-247, 257, 274, 294-316, 339-347, 364, 386-389, 405-408, 427-430, 436-442, 457, 472, 483, 505-509, 530-549, 555, 561, 567, 584, 587-594, 639-723
app/services/reminder_service.py                    75     19     20      2    74%   26-28, 35-37, 41-42, 50, 63, 77, 103, 138-140, 172-174, 200-201, 205
app/services/reward_export_service.py              133    110     30      0    15%   31-33, 67-238
app/services/reward_report_service.py               65     36     18      2    37%   50-51, 75, 79-117, 125-148, 151-183, 186-189, 223-232
app/services/reward_service.py                     203     97     64      3    45%   43-45, 50-52, 65->80, 68, 75-76, 78, 116->118, 119, 130-134, 136, 145-147, 149, 156, 158-163, 193-198, 223-226, 228, 231, 236, 251-256, 260-300, 313-325, 342-385, 401-406, 414-417, 423
app/services/role_service.py                        40      8      6      2    74%   20, 31, 43, 50, 62, 68->70, 71, 87-88
app/services/salary_export_service.py              127     16     40      2    87%   39->41, 43->45, 53-55, 232, 247-261
app/services/salary_service.py                     253    119     66      2    48%   81, 149-150, 154-155, 172-203, 211-212, 234-238, 242-245, 251-253, 255-257, 279-285, 299-300, 320-321, 333, 382-383, 392-393, 400-428, 432-434, 438-439, 441-444, 446, 448-450, 454-493, 497-519, 523, 534-537, 570, 576-583, 605, 608-618, 628-629, 652-654, 692-693, 713-731, 854, 864-878, 893-902, 925, 928-942
app/services/training_course_service.py             82     46     34      3    35%   30-32, 68-69, 79, 81, 86, 89, 99, 107-123, 125, 135-161, 163, 177-181, 183-186
app/services/training_export_service.py            148     90     34      0    34%   35-37, 98-127, 131-158, 168-256
app/services/training_plan_service.py              144     70     50      9    43%   38, 49->54, 51->54, 115, 117, 119, 121, 136, 144-151, 158-159, 167, 174-177, 187, 199-201, 216, 226-232, 234, 239-244, 249-256, 258, 263-270, 272, 283, 292-293, 299-300, 311-325, 327, 344-357, 359, 375-380
app/services/training_record_service.py            162     78     72      5    43%   40-42, 62, 64-66, 123, 125, 130, 134, 170-171, 174-175, 178, 183, 192-193, 196-201, 203-204, 214-232, 244-267, 274, 286-289, 302-323, 335-344, 346-360, 363, 374-377
app/services/training_report_service.py            136    100     60      1    20%   66, 73-75, 77-84, 95, 97-110, 112-138, 141-143, 156-180, 191, 194-204, 208-217, 249-257, 266-319
app/services/user_service.py                        66     18     16      2    71%   26, 56, 70, 77, 81, 105, 121-132, 134, 146-150
app/services/yearly_review_service.py              135     40     42      4    64%   59, 75-77, 95, 97-98, 112, 128-131, 133-134, 143->147, 149, 175-176, 183, 194, 241, 267-271, 274-275, 278, 287, 293-294, 304-319, 331-342, 349
app/utils/excel_style.py                            46      0     12      1    98%   34->41
app/workers/export_tasks.py                         20      4      0      0    80%   33-35, 45
app/workers/tasks.py                                92     42     16      0    50%   44, 85, 89-108, 114, 118-153, 192-200
--------------------------------------------------------------------------------------------
TOTAL                                            22694   6777   4462    524    64%

66 files skipped due to complete coverage.
Coverage HTML written to dir htmlcov
