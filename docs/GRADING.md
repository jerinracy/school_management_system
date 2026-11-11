# Bangladesh National Curriculum (GPA 5.0) Grading Standard & Engine

This document defines the mathematical formulation, academic rules, and architectural implementation of the grading and tabulation engine in the School Management System.

---

## 1. Grade Scale (Ministry of Education, Bangladesh)

The standard secondary (SSC) and higher secondary (HSC) grading system follows a 7-tier scale with maximum **GPA 5.00** and passing **GPA 1.00**:

| Marks Range (%) | Letter Grade | Grade Point | Remarks (EN) | Remarks (BN) |
|:---:|:---:|:---:|:---:|:---:|
| 80% – 100% | **A+** | **5.00** | Outstanding | অসাধারণ |
| 70% – 79.99% | **A** | **4.00** | Excellent | চমৎকার |
| 60% – 69.99% | **A-** | **3.50** | Very Good | খুব ভালো |
| 50% – 59.99% | **B** | **3.00** | Good | ভালো |
| 40% – 49.99% | **C** | **2.00** | Satisfactory | সন্তোষজনক |
| 33% – 39.99% | **D** | **1.00** | Pass | উত্তীর্ণ |
| 0% – 32.99% | **F** | **0.00** | Fail | ব্যর্থ |

---

## 2. Component Marks & Pass Policies

Secondary curriculum examinations partition subject papers into three possible components:
1. **CQ (Creative Question / Written)**
2. **MCQ (Multiple Choice Questions)**
3. **Practical**

### Configurable Pass Policies (`pass_policy`):
- `all_components`: Each component having a configured pass mark must be passed independently **AND** total marks must meet or exceed the total pass mark. If an examinee achieves 80/100 overall but scores 8/30 in MCQ (pass mark 10), the subject status is **Fail (F / 0.00)**.
- `overall_aggregate`: The student passes as long as the sum of all components meets or exceeds the subject pass mark.
- `theory_practical_separate`: Theory (CQ + MCQ) is evaluated collectively against the theory pass mark, while Practical is evaluated independently.

---

## 3. Combined Papers (1st & 2nd Paper)

Subjects such as Bangla and English are divided into two 100-mark papers (200 marks total):
- Paper 1 (100 marks) + Paper 2 (100 marks) = 200 marks full paper.
- Under board rules, a student must obtain a minimum of **66 marks out of 200** (33%) across both papers combined to pass.
- Even if a student scores 28 in Paper 1 and 42 in Paper 2 (Total = 70/200), the student passes with Grade **D** (35%).

---

## 4. 4th Subject (Optional Subject) Handling

In secondary and higher secondary levels (Classes 9–12), students take compulsory subjects plus one designated **4th Subject** (e.g. Higher Math, Biology, Agriculture, Computer Studies).

### 4th Subject Rules:
1. **Points Above 2.00 Are Added**: Only grade points obtained above **2.00** (Grade C) in the 4th subject count as bonus points toward the numerator.
   $$\text{Bonus Points} = \max(0.00, \text{Fourth Subject GPA} - 2.00)$$
2. **Denominator Excludes 4th Subject**: The total points (sum of mandatory subjects + bonus) are divided strictly by the number of mandatory subjects ($N_{\text{mandatory}}$).
   $$\text{Final GPA} = \min\left(5.00, \frac{\sum_{i=1}^{N_{\text{mandatory}}} \text{GPA}_i + \text{Bonus Points}}{N_{\text{mandatory}}}\right)$$
3. **Capping at 5.00**: Final GPA cannot exceed **5.00** (Golden GPA).
4. **Failing 4th Subject Does Not Fail the Student**: If a student fails the 4th subject (Grade F / 0.00), zero bonus points are added, but the student still passes if all mandatory subjects are passed.

---

## 5. Mandatory Fail Rule

> **Important**: Under Bangladesh National Curriculum rules, if an examinee fails (**Grade F / 0.00**) or is **Absent** in **any** compulsory/mandatory subject, the examinee's final result is automatically **Fail (Grade F / GPA 0.00)**, regardless of scoring GPA 5.00 in all other subjects.

---

## 6. Deterministic Merit Ranking & Tie-Breaking

When sorting students for merit positions (within a class section or across the whole class level):
1. **Passed Candidates First**: All passed candidates (`is_passed = True`) precede failed candidates (`is_passed = False`).
2. **Final GPA Descending**: Higher GPA ranks higher.
3. **Total Marks Obtained Descending**: In case of identical GPAs, the student with higher total marks across all papers ranks higher.
4. **Section Roll Number Ascending**: In case of identical total marks, the lower roll number serves as the final tie-breaker.

---

## 7. Multi-Term Cumulative Result & Promotion

For academic sessions with multiple terms (e.g. Term 1 [30%] + Annual [70%]):
$$\text{Cumulative Marks} = \sum (\text{Term Marks} \times \text{Weight \%})$$
$$\text{Cumulative CGPA} = \sum (\text{Term GPA} \times \text{Weight \%})$$

### Promotion Recommendation:
A student is flagged as `promotion_recommended = True` if:
- The student passed all terms or the final annual examination.
- The cumulative CGPA meets or exceeds the passing threshold ($\ge 1.00$).

---

## 8. Hand-Verified Golden Test Cases

### Golden Case 1: All Subjects Passed without 4th Subject
- 6 Mandatory Subjects:
  - Bangla (Combined): 85% -> GP 5.00
  - English (Combined): 82% -> GP 5.00
  - Mathematics: 75% -> GP 4.00
  - General Science: 65% -> GP 3.50
  - Social Science: 72% -> GP 4.00
  - Religion: 88% -> GP 5.00
- **Calculation**:
  $$\text{Sum} = 5.00 + 5.00 + 4.00 + 3.50 + 4.00 + 5.00 = 26.50$$
  $$\text{GPA} = \frac{26.50}{6} = 4.4166\dots \approx 4.42 \implies \text{Grade A}$$

### Golden Case 2: 4th Subject Bonus Elevates to GPA 5.00
- 6 Mandatory Subjects:
  - 5 subjects with GP 5.00 (Total = 25.00)
  - 1 subject with GP 4.00 (Total = 4.00)
  - Sum Mandatory = $25.00 + 4.00 = 29.00$
  - GPA without 4th = $29.00 / 6 = 4.83$ (Grade A)
- 4th Subject (Higher Math):
  - Score: 85% -> GP 5.00
  - Bonus Points = $\max(0, 5.00 - 2.00) = 3.00$
- **Final Calculation**:
  $$\text{Numerator} = 29.00 + 3.00 = 32.00$$
  $$\text{Final GPA} = \min\left(5.00, \frac{32.00}{6}\right) = \min(5.00, 5.33) = \mathbf{5.00} \implies \text{Grade A+}$$

### Golden Case 3: Failed One Mandatory Subject
- 5 Mandatory Subjects with GP 5.00
- 1 Mandatory Subject (English) with GP 0.00 (Score 28% -> Grade F)
- 4th Subject with GP 5.00
- **Result**:
  - `is_passed = False`
  - `final_gpa = 0.00`
  - `final_grade = "F"`
  - `failed_subjects_summary = ["English"]`
