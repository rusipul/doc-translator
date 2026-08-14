import json
from openai import OpenAI

BATCH_SIZE = 50

_LANG_NAMES = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "vi": "Vietnamese",
}


class TranslateError(Exception):
    pass


def batch_translate(
    texts: list[str],
    target_lang: str,
    api_key: str,
    source_lang: str | None = None,
) -> list[str]:
    if not texts:
        return []
    if not api_key:
        raise TranslateError("API key is not set")

    lang_name = _LANG_NAMES.get(target_lang, target_lang)
    client = OpenAI(api_key=api_key)
    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i: i + BATCH_SIZE]

        # Use numbered keys so the model cannot merge or skip items
        numbered = {str(j): text for j, text in enumerate(chunk)}
        prompt = (
            f"Translate the following texts to {lang_name}. "
            "The input is a JSON object where keys are numeric indices and values are texts to translate. "
            "Return a JSON object with the same numeric keys and translated strings as values. "
            "Every key must be present in the output. Do not add explanations.\n\n"
            f"Input: {json.dumps(numbered, ensure_ascii=False)}"
        )

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            f"You are a professional translator specializing in semiconductor and electronics manufacturing business documents. "
                            f"Translate each text naturally and idiomatically into {lang_name}. "
                            "These texts are extracted from quality reports, production summaries, meeting minutes, and internal business communications.\n\n"

                            "## CRITICAL RULES (Never violate)\n"
                            "1. Korean person names (e.g. 박광수, 신규상, 류진규) MUST be romanized (Park Kwang-soo, Shin Gyu-sang, Ryu Jin-kyu). NEVER translate a person's name by its meaning.\n"
                            "2. 'XX년 누적' or 'XXY 누적' means year-to-date cumulative for year 20XX, NOT 'for XX years'. Translate as '20XX YTD cumulative' or '20XX cumulative'.\n"
                            "3. Do NOT insert '→' arrows that are not in the original text. Wide spaces or line breaks in the source should become ':' or '—' or a natural sentence break.\n"
                            "4. Never leave source-language words untranslated.\n"
                            "5. 1Q/2Q/3Q/4Q → Q1/Q2/Q3/Q4 (apply consistently throughout the entire document).\n\n"

                            "## Date & Time\n"
                            "- KO months: 1월→Jan, 2월→Feb, 3월→Mar, 4월→Apr, 5월→May, 6월→Jun, "
                            "7월→Jul, 8월→Aug, 9월→Sep, 10월→Oct, 11월→Nov, 12월→Dec\n"
                            "- ZH months: 1月→1월/Jan, 2月→2월/Feb, 3月→3월/Mar, 4月→4월/Apr, "
                            "5月→5월/May, 6月→6월/Jun, 7月→7월/Jul, 8月→8월/Aug, "
                            "9月→9월/Sep, 10月→10월/Oct, 11月→11월/Nov, 12月→12월/Dec\n"
                            "- JA months: same as ZH months above\n"
                            "- Half-year: 상반기/上半年→H1 (First Half), 하반기/下半年→H2 (Second Half)\n"
                            "- Quarters: 1분기/1Q/第一季度→Q1, 2분기/2Q/第二季度→Q2, "
                            "3분기/3Q/第三季度→Q3, 4분기/4Q/第四季도→Q4\n"
                            "- Date format: keep YYYY-MM-DD as-is in technical documents; apply consistently within a slide\n\n"

                            "## Quality & Manufacturing Terms\n"
                            "- 불량률/不良率→Defect Rate (unit: ppm)\n"
                            "- 고객불량율/客户不良率→Customer Defect Rate / Field Defect Rate\n"
                            "- 수율/良率/歩留まり→Yield Rate [良率(ZH)→수율(KO), NOT 양호율]\n"
                            "- 이상 Lot→Abnormal Lot [NOT Excess Lot]\n"
                            "- 불량 현상→Failure Mode / Failure Symptom [NOT Defect Phenomenon]\n"
                            "- 1ppm 내,외 수준→around/approximately 1ppm level [NOT 'within 1ppm']\n"
                            "- 양산성평가→Mass Production Readiness Evaluation/Assessment [NOT Production Evaluation]\n"
                            "- 개발완료심의→Development Completion Review / Design Qualification Review\n"
                            "- 封装(ZH)→패키징(KO)/Packaging(EN) [NOT 포장]\n"
                            "- 晶圆(ZH)→웨이퍼(KO)/Wafer(EN)\n"
                            "- 芯片(ZH)→칩(KO)/Chip(EN)\n"
                            "- 개선대책/改善对策/是正処置→Corrective Action\n"
                            "- 整改(ZH)→시정조치(KO)/Corrective Action(EN) [NOT left untranslated]\n"
                            "- 闭环(ZH)→완결/클로징(KO)/Closed-loop Closing(EN) [NOT 폐쇄]\n"
                            "- 二方审核(ZH)→2자 심사(KO)/Bilateral Audit(EN) [NOT 이차 심사]\n"
                            "- 台账(ZH)→관리 대장(KO)/Register(EN) [NOT 계정]\n"
                            "- 卡点(ZH)→관문/병목(KO)/Critical Gate/Bottleneck(EN) [NOT 카드 포인트]\n"
                            "- 上线(ZH)→가동/출시(KO)/Go-Live/Launch(EN)\n"
                            "- 审核(ZH)→심사/감사(KO)/Audit(EN)\n"
                            "- 분쟁/책임 광물→Conflict/Responsible Minerals [NOT responsibility mineral]\n"
                            "- 원인분석/原因分析→Root Cause Analysis\n"
                            "- 재발방지/防止再发→Recurrence Prevention\n"
                            "- 공정/工序/工程→Process\n"
                            "- 가동률/开动率/稼働率→Operation Rate\n"
                            "- 생산량/产量/生産量→Production Volume\n"
                            "- 납기/交期/納期→Delivery Date\n"
                            "- 검사/检验/検査→Inspection\n"
                            "- 공급망/供应链→Supply Chain\n\n"

                            "## Status & Progress\n"
                            "- 진행중/进行中/進行中→In Progress\n"
                            "- 완료/完成/完了→Completed\n"
                            "- 검토중/审核中→Under Review\n"
                            "- 보류/暂停→On Hold\n"
                            "- 미완료/未完成→Incomplete\n"
                            "- 예정/计划/予定→Planned\n"
                            "- 지연/延迟/遅延→Delayed\n"
                            "- 已完成→완료/Completed\n"
                            "- 待确认→Pending Confirmation\n\n"

                            "## Business & Document Terms\n"
                            "- 담당자/负责人/担当者→Person in Charge\n"
                            "- 협력사/供应商→Supplier\n"
                            "- 발주/订单/発注→Purchase Order (PO)\n"
                            "- 총결보고/总结报告→Summary Report\n"
                            "- 현황/现状/現状→Status / Current Status\n"
                            "- 조치사항/措施事项→Action Items\n"
                            "- 추진내용→Action Details / Activity Details [NOT Initiative Details]\n"
                            "- 작성 내용 (table header)→Response Description / Action Taken [NOT Written content]\n"
                            "- 향후 계획→Action Plan / Future Plans [translate, do NOT leave in Korean]\n"
                            "- 발생 현황(누적)→Occurrence Status (Cumulative) [translate, do NOT leave in Korean]\n"
                            "- 기한/截止日期/期限→Deadline\n"
                            "- 목표/目标/目標→Target\n"
                            "- 실적/实绩/実績→Actual Results\n"
                            "- 달성률/达成率/達成率→Achievement Rate\n"
                            "- 고객/客户/顧客→Customer\n"
                            "- 완성차 고객/整车客户→OEM Customer\n"
                            "- 속지/属地(ZH)→현지/Local\n"
                            "- 건(件)→case(s) (예: 2건→2 cases)\n\n"

                            "## Punctuation Rules\n"
                            "- Replace CJK punctuation with target-language equivalents\n"
                            "- 。→ .  /  ，→ ,  /  ：→ :  /  ；→ ;  /  「」→ quotes\n"
                            "- Do NOT leave Chinese or Japanese punctuation in the output\n\n"

                            "## General Rules\n"
                            "- Preserve as-is: numbers, model/part codes, abbreviations (PPM, SQE, Cpk, QA, QC, PO, VDA, ISO, IATF, FAB, PT, FT, AOI, SBL, SYL, CIP, etc.)\n"
                            "- Keep symbols unchanged: %, /, -, _, ·, →, ±\n"
                            "- Company/brand names: keep original or use widely accepted transliteration\n"
                            "- For Japanese output: formal business style (です/ます調)\n"
                            "- For Chinese output: Simplified Chinese standard business terminology\n"
                            "- Short fragments: infer from semiconductor/manufacturing business context\n"
                            "- Never add explanations, parentheses, or notes to the translation"
                        )},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                body = json.loads(response.choices[0].message.content)
                # Reconstruct in original order by numeric key
                translated = [body[str(j)] for j in range(len(chunk))]
                results.extend(translated)
                last_exc = None
                break
            except (KeyError, TypeError) as e:
                last_exc = TranslateError(f"Unexpected response format: {e}")
            except Exception as e:
                last_exc = e

        if last_exc is not None:
            raise TranslateError(str(last_exc)) from last_exc

    return results
