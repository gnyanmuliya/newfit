import streamlit as st
import requests
from typing import Dict, List, Optional, Set, Any
import re
from datetime import datetime
import pandas as pd
import json
import numpy as np # Used for safe NaN handling

# ============ CONFIGURATION ============
# NOTE: The API key and Endpoint URL are set for an Azure Mistral deployment.
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(
    page_title="FriskaAI Fitness Coach",
    page_icon="💪",
    layout="wide"
)

# ============ LOAD EXCEL CONDITION DATABASE ============
@st.cache_data
def load_condition_database():
    """Load condition database from Excel file"""
    try:
        # CRITICAL: Ensure the Excel file name is correct and accessible
        # NOTE: Since the file itself is not provided, this assumes a mock or environment access
        # If running locally, ensure 'Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx' is in the same directory.
        try:
            df = pd.read_excel("Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx")
        except FileNotFoundError:
            # Create an empty DataFrame if the file isn't found to prevent crash
            df = pd.DataFrame(columns=['Condition', 'Medication(s)', 'Direct Exercise Impact', 'Indirect Exercise Impacts', 'Contraindicated Exercises', 'Modified / Safer Exercises'])

        condition_db = {}
        if 'Condition' not in df.columns:
            return {}
            
        for _, row in df.iterrows():
            condition_name = row['Condition']
            condition_db[condition_name] = {
                'medications': row.get('Medication(s)', np.nan),
                'direct_impact': row.get('Direct Exercise Impact', np.nan),
                'indirect_impact': row.get('Indirect Exercise Impacts', np.nan),
                'contraindicated': row.get('Contraindicated Exercises', np.nan),
                'modified_safer': row.get('Modified / Safer Exercises', np.nan)
            }
            # Replace NaN with empty string for clean output in prompt
            for key in condition_db[condition_name]:
                if pd.isna(condition_db[condition_name][key]):
                    condition_db[condition_name][key] = ""
                    
        return condition_db
    except Exception as e:
        # Fallback to an empty database on any loading failure
        return {}

# Load condition database
CONDITION_DATABASE = load_condition_database()

# ============ MEDICAL CONDITIONS LIST (NO CHANGE) ============
MEDICAL_CONDITIONS = [
    "None",
    "Hypertension (High Blood Pressure)",
    "Type 2 Diabetes",
    "Coronary Artery Disease",
    "Osteoarthritis",
    "Chronic Lower Back Pain",
    "Obesity",
    "Asthma",
    "COPD (Chronic Obstructive Pulmonary Disease)",
    "Osteoporosis",
    "Depression/Anxiety",
    "Stroke (Post-Recovery)",
    "Heart Failure",
    "Peripheral Artery Disease",
    "Rheumatoid Arthritis",
    "Sleep Apnea",
    "Chronic Kidney Disease",
    "Fatty Liver Disease",
    "PCOS (Polycystic Ovary Syndrome)",
    "Fibromyalgia",
    "Multiple Sclerosis",
    "Parkinson's Disease",
    "Cancer (During/Post Treatment)",
    "Other"
]

# ============ FITNESS LEVELS WITH RPE (NO CHANGE) ============
FITNESS_LEVELS = {
    "Level 1 – Assisted / Low Function": {
        "description": "Needs support for balance, limited endurance, sedentary >6 months. Prioritize seated or supported moves.",
        "exercises": "Chair exercises, wall push-ups, step taps, light bands",
        "rpe_range": "3-4",
        "scaling_note": "Focus on **seated, supported, or assisted movements**. Exercises should be simple and focus on **functional stability** and **basic range of motion**."
    },
    "Level 2 – Beginner Functional": {
        "description": "Can perform light bodyweight tasks, mild conditions under control. Can sustain 10-15 min activity.",
        "exercises": "Slow tempo bodyweight + mobility drills",
        "rpe_range": "4-5",
        "scaling_note": "Focus on **standing bodyweight movements with stable support if needed**. Introduce **light resistance bands** and maintain **slow, controlled tempo**."
    },
    "Level 3 – Moderate / Independent": {
        "description": "Can perform unassisted movements with mild fatigue. Regular activity 2-3x/week.",
        "exercises": "Resistance bands, light weights, low-impact cardio",
        "rpe_range": "5-7",
        "scaling_note": "Focus on **unassisted bodyweight** and **external resistance (light dumbbells/bands)**. Introduce **compound movements** and simple cardio intervals."
    },
    "Level 4 – Active Wellness": {
        "description": "No severe limitations, accustomed to regular activity. Good movement quality.",
        "exercises": "Moderate intensity strength + balance training, varied equipment",
        "rpe_range": "6-8",
        "scaling_note": "Focus on **moderate to high-intensity training**. Introduce **advanced variations of compound lifts**, single-leg work, and **progressive overload techniques**."
    },
    "Level 5 – Adaptive Advanced": {
        "description": "Experienced user managing mild conditions. Consistent training 4-6x/week.",
        "exercises": "Structured strength split, low-impact cardio, yoga",
        "rpe_range": "7-9",
        "scaling_note": "Focus on **heavy resistance and high volume/intensity**. Implement **structured splits**, complex movements (e.g., loaded single-leg work), and **advanced programming techniques**."
    }
}

class FitnessAdvisor:
    """Enhanced fitness planning engine with proper API integration"""
    
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        
        self.goal_programming_guidelines = {
            "Weight Loss": {
                "priority": "Low to moderate-intensity cardio + full-body resistance. Adjust cardio/resistance ratio (Cardio should be 60-70% of main workout time).",
                "rep_range": "12-20",
                "rest": "30-45 seconds (Short rest for metabolic stress)",
                "sets": "2-3",
                "focus_type": "Metabolic, circuit-style, full-body movements."
            },
            "Muscle Gain": {
                "priority": "Prioritize progressive overload resistance training with RPE 6-8, controlled tempo (3-1-3), and sufficient rest. Target 3-5 sets per exercise.",
                "rep_range": "6-12",
                "rest": "60-90 seconds (Moderate rest for strength/hypertrophy)",
                "sets": "3-5",
                "focus_type": "Hypertrophy-focused, controlled tempo, progressive resistance."
            },
            "Increase Overall Strength": {
                "priority": "Compound lifts and progressive loading, adjusted for fitness level. Focus on moderate volume, high load (if appropriate for level).",
                "rep_range": "4-8",
                "rest": "90-180 seconds (Long rest for maximal strength recovery)",
                "sets": "3-5",
                "focus_type": "Strength-focused, heavy compound movements, accessory stability."
            },
            "Improve Cardiovascular Fitness": {
                "priority": "Aerobic/interval protocols scaled to level (60-80% max HR). Include recovery days and low-impact options for older/obese users.",
                "rep_range": "N/A (Time or Distance based)",
                "rest": "N/A (Active recovery or interval rest)",
                "sets": "N/A",
                "focus_type": "Cardio-respiratory endurance, interval training, low-impact."
            },
            "Improve Flexibility & Mobility": {
                "priority": "Emphasize stretching, joint mobility, dynamic range of motion, and breathing control. Focus on full ROM and static holds.",
                "rep_range": "30-60 seconds hold duration per side",
                "rest": "15 seconds between sides",
                "sets": "1-2",
                "focus_type": "Mobility, dynamic stretching, full range of motion."
            },
            "Rehabilitation & Injury Prevention": {
                "priority": "Prioritize corrective, stability, and low-load resistance training. Focus on perfect form and exclude all contraindicated movements.",
                "rep_range": "10-15 (High repetition for endurance/form focus)",
                "rest": "60-90 seconds",
                "sets": "2-3",
                "focus_type": "Corrective, stability, perfect form, low-load resistance."
            },
            "Improve Posture and Balance": {
                "priority": "Focus on core activation, mobility, balance, and proprioceptive drills. Include single-leg work (if appropriate for level) and exercises for postural muscles.",
                "rep_range": "10-15 (or Time-based holds)",
                "rest": "45-60 seconds",
                "sets": "2-3",
                "focus_type": "Core stability, proprioception, postural muscle strengthening."
            },
            "General Fitness": {
                "priority": "Balanced approach: mix of cardio, strength, and flexibility.",
                "rep_range": "10-15",
                "rest": "45-60 seconds",
                "sets": "2-3",
                "focus_type": "Balanced, full-body circuit or supersets."
            }
        }
    
    def _get_condition_details_from_db(self, condition: str) -> Dict:
        """Get condition details from loaded database (NO CHANGE)"""
        if condition in CONDITION_DATABASE:
            return {k: v if v else 'N/A' for k, v in CONDITION_DATABASE[condition].items()}
        
        fallback_db = {
            "Hypertension (High Blood Pressure)": {
                "medications": "ACE inhibitors, Beta-blockers, Diuretics",
                "direct_impact": "May reduce exercise capacity, affect heart rate response",
                "indirect_impact": "Dizziness, fatigue",
                "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing without control, High-Intensity Interval Training (HIIT) without medical clearance.",
                "modified_safer": "Controlled breathing, moderate resistance, continuous breathing pattern, steady-state cardio."
            },
            "Type 2 Diabetes": {
                "medications": "Metformin, Insulin, Sulfonylureas",
                "direct_impact": "Risk of hypoglycemia during exercise",
                "indirect_impact": "Fatigue, neuropathy, vision issues",
                "contraindicated": "High-intensity intervals without medical clearance, prolonged fasting exercise, foot-stressing activities if neuropathy is present.",
                "modified_safer": "Moderate-intensity steady state, check blood glucose pre/post workout, low-impact weight-bearing, proper foot care."
            }
        }
        
        return fallback_db.get(condition, {
            "medications": "Unknown",
            "direct_impact": "Use conservative approach",
            "indirect_impact": "Monitor for symptoms (e.g., fatigue, pain)",
            "contraindicated": "High-risk movements (e.g., heavy lifting, ballistic movements, full spinal flexion/extension) due to unknown risk.",
            "modified_safer": "Low-impact, controlled movements, seated or supported alternatives."
        })

    def _determine_split_focus(self, total_days: int, day_index: int) -> str:
        """Determine the body part focus based on frequency and day index. (NO CHANGE)"""
        
        if total_days <= 2:
            return "Full Body Focus (Emphasis on major muscle groups)"
        elif total_days == 3:
            focus_map = {0: "Full Body Focus", 1: "Upper Body Focus", 2: "Lower Body Focus"}
            return focus_map.get(day_index % 3, "Full Body Focus")
        elif total_days == 4:
            focus_map = {0: "Upper Body Focus", 1: "Lower Body Focus", 2: "Upper Body Focus", 3: "Lower Body Focus"}
            return focus_map.get(day_index % 4, "Upper Body Focus")
        elif total_days >= 5:
            focus_map = {
                0: "Upper Body Strength Focus", 
                1: "Lower Body Strength Focus", 
                2: "Full Body Endurance Focus", 
                3: "Upper Body Volume Focus", 
                4: "Lower Body Volume Focus",
                5: "Core & Mobility Focus",
                6: "Active Recovery Focus"
            }
            return focus_map.get(day_index % 7, "Full Body Focus")
        
        return "Full Body Focus"
    
    def _determine_exercise_count(self, session_duration: str, fitness_level: str) -> str:
        """
        Determine the target number of main exercises based on duration, 
        ADJUSTED for fitness level to manage joint stress and volume.
        """
        duration_map = {
            "15-20 minutes": 17.5, 
            "20-30 minutes": 25, 
            "30-45 minutes": 37.5, 
            "45-60 minutes": 52.5
        }
        total_minutes = duration_map.get(session_duration, 37.5)
        
        # Base count based on duration (Original logic)
        if total_minutes <= 25:
            count = 4
        elif total_minutes <= 40:
            count = 6
        elif total_minutes <= 55:
            count = 7
        else:
            count = 8
            
        # Adjustment based on fitness level (Issue 2 fix)
        if fitness_level == "Level 1 – Assisted / Low Function":
            # Max 4 exercises for Level 1, prioritizing very low volume.
            if count > 4:
                 count = 4 
        elif fitness_level == "Level 2 – Beginner Functional":
             # Max 5 exercises for Level 2, balancing stress and progress.
            if count > 5:
                count = 5 
            
        return str(count)

    def _convert_plan_to_markdown_enhanced(self, plan_json: Dict) -> str:
        """
        Converts the structured JSON plan back into a user-friendly Markdown string 
        with strict, numbered formatting for ALL sections, as requested.
        """
        if not plan_json:
            return "Plan structure is missing or empty."

        markdown_output = ""
        
        # Helper function for formatting exercise blocks (used by all sections)
        def format_exercise_block(exercise_data: Dict, index: int, section_type: str) -> str:
            
            name = exercise_data.get('name', 'Exercise Name Missing')
            benefit = exercise_data.get('benefit', exercise_data.get('focus', 'N/A'))
            steps = exercise_data.get('steps', [])
            
            # Determine Rep/Duration/Hold label and value
            if section_type == 'main':
                rep_label = "Reps"
                rep_value = exercise_data.get('reps', 'N/A')
                set_label = "Sets"
                set_value = exercise_data.get('sets', 'N/A')
            elif section_type == 'warmup':
                rep_label = "Duration"
                rep_value = exercise_data.get('duration', 'N/A')
                set_label = "Sets" # Replaced by the intensity in prompt example, but included for structure consistency
                set_value = exercise_data.get('sets', '1') # Force 1 set for consistency
            elif section_type == 'cooldown':
                rep_label = "Hold Duration"
                rep_value = exercise_data.get('hold', 'N/A')
                set_label = "Sets"
                set_value = exercise_data.get('sets', '1') # Force 1 set for consistency
            else:
                rep_label = "Value"
                rep_value = "N/A"
                set_label = "Sets"
                set_value = "N/A"

            intensity_value = exercise_data.get('intensity_rpe', 'N/A').replace('RPE ', '')
            rest_value = exercise_data.get('rest', 'N/A')
            equipment = exercise_data.get('equipment', 'N/A')
            safety_cue = exercise_data.get('safety_cue', 'N/A')
            
            # Start of the strictly formatted output
            output = f"{index}. **{name}**\n\n"
            output += f"**Benefit:** {benefit}\n\n"
            output += "**How to Perform:**\n"
            
            # Indented list for steps
            if steps:
                for step_idx, step in enumerate(steps):
                    # Uses 4 spaces for strict indentation
                    output += f"     {step_idx + 1}. {step.strip()}\n"
            else:
                 output += f"     1. (Steps missing from plan - Follow general form)\n"
            
            output += f"\n**{set_label}:** {set_value}\n\n"
            output += f"**{rep_label}:** {rep_value}\n\n"
            output += f"**Intensity:** RPE {intensity_value}\n\n"
            output += f"**Rest:** {rest_value}\n\n"
            output += f"**Equipment:** {equipment}\n\n"
            output += f"**Safety Cue:** {safety_cue} (Prioritize stability and balance.)\n\n"
            
            return output
        
        # 1. Warm-Up 
        markdown_output += f"## 🤸 **Warm-Up** ({plan_json.get('warmup_duration', 'N/A')})\n\n"
        for idx, item in enumerate(plan_json.get('warmup', [])):
            markdown_output += format_exercise_block(item, idx + 1, 'warmup')
        markdown_output += "---\n"
        
        # 2. Main Workout
        markdown_output += f"## 💪 **Main Workout** ({plan_json.get('main_workout_category', 'N/A')})\n"
        
        # *** REMOVED: **Goal:** Achieve RPE {first_exercise_rpe} for all sets. ***
        
        for idx, exercise in enumerate(plan_json.get('main_workout', [])):
            markdown_output += format_exercise_block(exercise, idx + 1, 'main')
        markdown_output += "---\n"
        
        # 3. Cool-Down
        markdown_output += f"## 🧘 **Cool-Down** ({plan_json.get('cooldown_duration', 'N/A')})\n\n"
        for idx, item in enumerate(plan_json.get('cooldown', [])):
            markdown_output += format_exercise_block(item, idx + 1, 'cooldown')
        markdown_output += "---\n"

        # 4. Safety Notes (Progression tip removed from here, only safety tips remain)
        markdown_output += f"## 📝 **Safety and General Notes**\n"
        
        safe_notes = [note for note in plan_json.get('safety_notes', []) if not note.strip().lower().startswith("progression tip:")]
        
        if safe_notes:
            for idx, note in enumerate(safe_notes):
                markdown_output += f"**{idx + 1}.** {note}\n\n"
        else:
             markdown_output += "No specific safety notes provided for this session.\n\n"
        
        return markdown_output

    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        previous_plans: Dict, 
        workout_category: str = "Full Body"
    ) -> str:
        """
        Build a comprehensive, rules-based system prompt for workout plan generation,
        enforcing all user-requested constraints, including enhanced variety rules and safety checks.
        """
        
        # Extract profile
        name = user_profile.get("name", "User")
        age = user_profile.get("age", 30)
        gender = user_profile.get("gender", "Other")
        bmi = user_profile.get("bmi", 22)
        fitness_level = user_profile.get("fitness_level", "Level 3 – Moderate / Independent")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        physical_limitations = user_profile.get("physical_limitations", "")
        session_duration = user_profile.get("session_duration", "30-45 minutes")
        equipment_list = user_profile.get("available_equipment", ["Bodyweight Only"])
        total_training_days = len(user_profile.get("days_per_week", []))
        
        # --- Goal and Level Alignment ---
        level_data = FITNESS_LEVELS.get(fitness_level, FITNESS_LEVELS["Level 3 – Moderate / Independent"])
        level_rpe = level_data['rpe_range']
        
        goal_guidelines = self.goal_programming_guidelines.get(primary_goal, {})
        
        target_rpe = level_rpe
        target_sets = goal_guidelines.get('sets', '2-3')
        target_reps = goal_guidelines.get('rep_range', '10-15')
        target_rest = goal_guidelines.get('rest', '45-60 seconds')
        
        rpe_override_note = ""
        if primary_goal == "Muscle Gain" and fitness_level == "Level 2 – Beginner Functional":
            target_rpe = "5-7" 
            target_sets = "3"   
            rpe_override_note = (
                "**⚠️ RPE OVERRIDE FOR MUSCLE GAIN (Level 2):** You **MUST** target RPE 5-7. The effort used MUST be challenging enough to achieve RPE 5-7 by the last few reps. **Target 3 Sets.**"
            )
        
        # --- Duration and Exercise Count (Issue 2 Fix) ---
        max_main_exercises = self._determine_exercise_count(session_duration, fitness_level)
        
        # --- Dynamic Split Focus ---
        day_focus = self._determine_split_focus(total_training_days, day_index)
        
        # --- PROFILE SUMMARY --- (simplified for brevity, but all data is used)
        profile_summary = (
            f"- Name/ID: {name} | Gender: {gender} | Age: {age} | BMI: {bmi:.1f}\n"
            f"- Fitness Level: **{fitness_level}**\n"
            f"- Primary Goal: **{primary_goal}**\n"
            f"- **Session Duration (MUST FIT): {session_duration}**\n"
            f"- Available Equipment (MUST USE ONLY THIS): {', '.join(equipment_list)}\n"
            f"- **MEDICAL CONDITIONS (ZERO TOLERANCE):** {', '.join(medical_conditions)}\n"
            f"- **PHYSICAL LIMITATIONS (CRITICAL):** {physical_limitations if physical_limitations else 'None'}"
        )

        # --- VARIETY AND REPETITION AVOIDANCE LOGIC (User Request) ---
        exercises_to_avoid = []
        previous_plan_summary = ""
        
        previous_training_days = [d for d in user_profile.get('days_per_week', []) if user_profile.get('days_per_week', []).index(d) < day_index]
        
        if previous_training_days and previous_plans:
            last_day = previous_training_days[-1]
            last_plan_data = previous_plans.get(last_day)
            
            if last_plan_data and last_plan_data.get('success') and 'plan_json' in last_plan_data and last_plan_data['plan_json']:
                last_main_exercises = [
                    ex.get('name', '').strip() 
                    for ex in last_plan_data['plan_json'].get('main_workout', []) 
                    if ex.get('name')
                ]
                exercises_to_avoid = list(set(last_main_exercises)) 
            
            previous_plan_summary = "".join([
                f"- **{d}**: Exercises: {', '.join([ex.get('name', 'N/A') for ex in p.get('plan_json', {}).get('main_workout', []) if 'name' in ex])}\n" 
                for d, p in previous_plans.items() if p and p.get('plan_json')
            ])
            
        if not previous_plan_summary:
             previous_plan_summary = "- None. Ensure maximum variety."


        # --- START OF STRUCTURED PROMPT ---
        prompt_parts = []
        
        prompt_parts.append(f"""You are FriskaAI, an expert clinical exercise physiologist (ACSM-CEP).
Your primary role is to ensure **MAXIMUM SAFETY** (especially for Level 1/Medical Conditions/Limitations) while **OPTIMIZING FOR THE PRIMARY GOAL**.
You **MUST** adhere to all numbered rules. You MUST respond ONLY in JSON format EXACTLY as specified in Rule 4.
""")
        
        # --- Workout Structure (Rule 0 - JSON Schema Reference) ---
        
        prompt_parts.append(f"""
**0. ABSOLUTE TOP PRIORITY: THE JSON OUTPUT SCHEMA**
Your entire response **MUST** be a single, valid JSON object that strictly conforms to the following schema.
The JSON object **MUST** be enclosed in a single markdown code block (` ```json ... ``` `) and contain the following keys:
- `day_name` (string)
- `warmup_duration` (string, e.g., '5-7 minutes')
- `main_workout_category` (string, e.g., 'Full Body - Lower Focus')
- `cooldown_duration` (string, e.g., '5-7 minutes')
- `safety_notes` (list of 3-5 strings, following Rule 5.D, including one dedicated progression tip)

**STRICT STRUCTURES (ALL exercises MUST follow these):**

1. **For EACH 'main_workout' OBJECT** (list of **EXACTLY {max_main_exercises}** objects):
{{
    "name": str,
    "benefit": str,
    "steps": list of str (MUST be 3-5 complete, sequential steps),
    "sets": str (MUST be "{target_sets}"),
    "reps": str (MUST be "{target_reps}"),
    "intensity_rpe": str (MUST be "RPE {target_rpe}"),
    "rest": str (MUST be "{target_rest}"),
    "equipment": str (MUST be from available list),
    "safety_cue": str (Specific to user limitations/conditions)
}}

2. **For EACH 'warmup' OBJECT** (list of **EXACTLY 3** objects):
{{
    "name": str,
    "benefit": str,
    "steps": list of str (MUST be 3-5 complete, sequential steps),
    "sets": str (MUST be "1"),
    "duration": str (e.g., "30 seconds" or "10 reps / side"),
    "intensity_rpe": str (MUST be "RPE 1-3"),
    "rest": str (e.g., "15 seconds"),
    "equipment": str (MUST be from available list, typically Bodyweight),
    "safety_cue": str
}}

3. **For EACH 'cooldown' OBJECT** (list of **EXACTLY 3** objects):
{{
    "name": str,
    "benefit": str,
    "steps": list of str (MUST be 3-5 complete, sequential steps),
    "sets": str (MUST be "1"),
    "hold": str (e.g., "30-60 seconds / side"),
    "intensity_rpe": str (MUST be "RPE 1-3"),
    "rest": str (MUST be "15 seconds"),
    "equipment": str (MUST be from available list, typically Bodyweight),
    "safety_cue": str
}}
""")

        prompt_parts.append(f"""
**1. USER PROFILE & TARGETS (NON-NEGOTIABLE CONSTRAINTS):**
{profile_summary}
- **Workout Focus:** **{day_focus}**. Exercises **MUST** be selected to emphasize this focus today.
- **Goal Programming Focus:** {goal_guidelines.get('focus_type', 'Balanced')}.
""")

        prompt_parts.append(f"""
**2. VARIETY & REPETITION AVOIDANCE (CRITICAL MANDATE):**

A. **STRICT AVOIDANCE LIST:** You **MUST NOT** use the following exercises in the **Main Workout** today. This list is based on the immediate preceding training day.
- **EXERCISES TO AVOID:** **{', '.join(exercises_to_avoid) if exercises_to_avoid else 'None'}**
- **Rule:** If an exact exercise name is on the AVOID list, you must substitute it with a variation or a different movement pattern (e.g., if 'Push-ups' was used, use 'Incline Push-ups' or 'Wall Push-ups') to work the same muscle group. **DO NOT** use the exact name.

B. **General Variety:** Ensure maximum variation across the entire week.
- **Previous Workouts (for full weekly context):**
{previous_plan_summary}
- **Exercise Standard:** Only use **standard, US-based/international** fitness exercises. DO NOT generate random or unfamiliar movements.
""")

        # --- NEW: CRITICAL SAFETY & EXERCISE SELECTION MANDATES (Issues 1 & 3 Fix) ---
        
        critical_safety_rules = [
            "\n**3. CRITICAL SAFETY & EXERCISE SELECTION MANDATES:**"
        ]

        # A. Equipment Constraint (Issue 1 fix)
        if equipment_list == ["Bodyweight Only"]:
            critical_safety_rules.append("- **A. EQUIPMENT MANDATE:** You **MUST NOT** suggest any exercises that require external equipment (Dumbbell, Kettlebell, Barbell, Machine). Strictly avoid: 'Overhead Dumbbell Press', 'Bent-over Reverse Fly', 'Bicep Curl with Dumbbells'.")
        else:
            critical_safety_rules.append("- **A. EQUIPMENT MANDATE:** Only use the available equipment: {', '.join(equipment_list)}. The `equipment` field MUST reflect the specific equipment used.")


        # B. Level Complexity Rule (User Request)
        level_rules = {
            "Level 1 – Assisted / Low Function": "Choose supported or **assisted** exercises (e.g., wall squats, seated march, supported rows). **STRICTLY AVOID** standing balance challenges and unassisted core work.",
            "Level 2 – Beginner Functional": "Use **low-impact, bodyweight-based functional** exercises. Prioritize stability. **STRICTLY AVOID** advanced balance moves (unassisted lunges) or high-impact moves.",
            "Level 3 – Moderate / Independent": "Include **moderate functional and resistance** exercises. Introduce compound movements and light instability.",
            "Level 4 – Active Wellness": "Provide balanced strength, stability, and endurance training with varied equipment and moderate intensity/volume.",
            "Level 5 – Adaptive Advanced": "Offer full-intensity, **functional, compound, and loaded stability** movements. Use advanced resistance/techniques."
        }
        
        critical_safety_rules.append(f"- **B. EXERCISE COMPLEXITY RULE (MANDATORY):** The exercises **MUST** strictly adhere to the rule for the selected level:\n    - **{fitness_level}:** {level_rules.get(fitness_level, 'Balanced approach.')}")

        # C. Advanced/High-Risk Movement Avoidance (Issue 3 fix)
        if fitness_level in ["Level 1 – Assisted / Low Function", "Level 2 – Beginner Functional"] or bmi > 30:
            advanced_exercises_to_avoid = [
                "Plank Shoulder Taps", "Full Lunges", "Reverse Lunges (unassisted)", "Burpees", "Box Jumps", 
                "Pistol Squats", "Single-leg Deadlifts (unassisted)", "Full Sit-ups"
            ]
            safer_alternatives_tip = "PRIORITIZE SAFER MOVES: Modified Bird-Dog, Assisted Lunges (holding chair/wall), Incline Push-ups (wall/bench), Step-ups, and Seated/Supported Core Holds."
            
            critical_safety_rules.append(f"- **C. BEGINNER/BMI MOVEMENT RESTRICTION:** Given the Level/BMI, you **MUST AVOID** high-balance/high-impact/high-joint-stress moves. Strictly avoid: {', '.join(advanced_exercises_to_avoid)}.")
            critical_safety_rules.append(f"- **D. BEGINNER/BMI MOVEMENT PRIORITY:** {safer_alternatives_tip}")

        prompt_parts.append('\n'.join(critical_safety_rules))
        
        
        # --- Medical Condition Rules Insertion (Rule 4) ---
        medical_conditions_text = ""
        if medical_conditions and medical_conditions != ["None"]:
            medical_conditions_text += f"""
\n**4. CONDITION-SPECIFIC SAFETY RULES (MANDATORY GUIDELINES):**
"""
            for condition in medical_conditions:
                if condition != "None":
                    cond_data = self._get_condition_details_from_db(condition)
                    medical_conditions_text += (
                        f"- **{condition} (Rule 4.A):**\n"
                        f"    - ❌ CONTRAINDICATED (MUST AVOID): {cond_data.get('contraindicated', 'High-risk movements')}\n"
                        f"    - ✓ MODIFIED/SAFER (PRIORITIZE): {cond_data.get('modified_safer', 'Low-impact alternatives')}\n"
                        f"    - Medication Note: {cond_data.get('medications', 'Unknown')}.\n"
                    )
            prompt_parts.append(medical_conditions_text)
            
        # --- CORE DIRECTIVES (Shifted to Rule 5) ---
        
        prompt_parts.append(f"""
**5. CORE DIRECTIVES (THESE ARE MANDATORY RULES):**
 
A. GOAL PROGRAMMING TARGETING (ABSOLUTELY CRITICAL):
- **Intensity Goal (RPE):** The final **intensity_rpe** for all main exercises **MUST** be **RPE {target_rpe}**. WARM-UP/COOL-DOWN MUST BE RPE 1-3.
- **Volume Goal (Sets/Reps/Rest):** The plan **MUST** apply the following structure exactly: Sets: **{target_sets}**, Reps: **{target_reps}**, Rest: **{target_rest}**.
- **Time Goal (CRITICAL IMPROVEMENT):** The plan should use **EXACTLY {max_main_exercises}** main exercises. This number is tailored for your specific level and duration to manage joint stress and volume.

{rpe_override_note}

B. EXERCISE DETAIL MANDATE (ACCURACY FIX):
- For all workout exercises (Warm-up, Main, Cooldown), the `steps` list **MUST** be highly accurate, formal, and complete. It must contain **3-5 distinct, easy-to-follow steps** that fully describe the exercise technique. The steps MUST match the US standard form of the exercise name exactly.

C. WARM-UP / COOL-DOWN MANDATE:
- The `warmup` and `cooldown` sections **MUST** contain **EXACTLY 3** objects each. The structure must match the JSON schema in Rule 0.

D. SAFETY NOTE GENERATION & PROGRESSION TIP:
- The `safety_notes` list **MUST** contain 3-5 tips.
    1. **Top Priority - Safety/Limitation:** Your first tip **MUST** be a practical safety recommendation directly related to managing the **Medical Condition** or **Physical Limitation**.
    2. **Second Priority - PROGRESSION TIP (MANDATORY):** One tip **MUST** be explicitly labeled "Progression Tip: [Actionable suggestion]". This tip will be extracted and used for the weekly plan. E.g., "Progression Tip: Next week, increase all reps by 2 or decrease rest by 15 seconds."
    3. **General Wellness:** Add 1-2 additional general health tips (e.g., emphasizing hydration, proper form, or breathing).
""")

        prompt_parts.append(f"""
**6. FINAL VALIDATION CHECKLIST (MANDATORY VERIFICATION):**
- **Format Check:** Is the entire output a single, valid JSON object inside a ```json block?
- **Count Check:** Does the `main_workout` list contain **EXACTLY {max_main_exercises}** exercise objects?
- **Warmup/Cooldown Check:** Do `warmup` and `cooldown` each contain **EXACTLY 3** objects, and do ALL objects contain the mandatory `steps` field?
- **Programming Check:** Are the Sets (**{target_sets}**), Reps (**{target_reps}**), Rest (**{target_rest}**), and RPE (**RPE {target_rpe}**) values correctly applied to **every** main exercise object?
- **Safety Check:** Are the **CRITICAL SAFETY MANDATES** from Rule 3 fully observed (Equipment and Level/BMI restrictions)?
- **Repetition Check:** Are all exercises in the `main_workout` **NOT** included in the **EXERCISES TO AVOID** list from Rule 2?
 
**7. TASK:**
- Generate the complete structured JSON workout plan for **{day_name}** adhering to all directives.
""")
 
        return "\n".join(prompt_parts)
    
    def _extract_and_move_progression_tip(self, plan_json: Dict) -> str:
        """Extracts the mandatory progression tip and removes it from the daily notes. (NO CHANGE)"""
        progression_tip = "Progression Tip: Next week, aim for an RPE increase of 0.5 or add 1-2 more reps." # Default Tip
        
        if 'safety_notes' in plan_json:
            new_notes = []
            for note in plan_json['safety_notes']:
                if note.strip().lower().startswith("progression tip:"):
                    # Capture the tip and remove the prefix
                    progression_tip = note.strip().replace("Progression Tip:", "").strip()
                else:
                    new_notes.append(note)
            
            # Update the safety notes to exclude the extracted tip
            plan_json['safety_notes'] = new_notes
            
        return progression_tip

    def generate_workout_plan(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        previous_plans: Dict, 
        workout_category: str = "Full Body"
    ) -> Dict:
        """Generate workout plan with fixed API call and JSON parsing."""
        
        goal = user_profile.get("primary_goal", "General Fitness")
        target_sets = self.goal_programming_guidelines.get(goal, {}).get('sets', '3')
        target_reps = self.goal_programming_guidelines.get(goal, {}).get('rep_range', '12')
        target_rest = self.goal_programming_guidelines.get(goal, {}).get('rest', '60 seconds')
        day_focus = self._determine_split_focus(len(user_profile.get("days_per_week", [])), day_index)
        
        fallback_plan_json = self._generate_fallback_plan_json(
            user_profile, 
            day_name, 
            day_focus,
            target_sets,
            target_reps,
            target_rest
        )
        
        progression_tip = "Maintain current routine and focus on perfect form." # Default Tip

        try:
            # Build the system prompt
            system_prompt = self._build_system_prompt(
                user_profile, day_name, day_index, previous_plans, workout_category
            )
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" 
            }
            
            payload = {
                "model": "mistral-small",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, an expert clinical exercise physiologist. Prioritize safety and follow all instructions, especially the JSON output format, strictly."},
                    {"role": "user", "content": system_prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 4096
            }
            
            # Note: In a real environment, you would implement exponential backoff here.
            response = requests.post(self.endpoint_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "plan_json": fallback_plan_json,
                    "plan_md": self._convert_plan_to_markdown_enhanced(fallback_plan_json),
                    "error": f"API returned {response.status_code} with error: {response.text}",
                    "progression_tip": progression_tip 
                }
            
            result = response.json()
            plan_text = result['choices'][0]['message']['content'] if 'choices' in result and result['choices'] else ""

            if not plan_text or len(plan_text) < 100:
                # Fallback to simple JSON parsing if the markdown block wasn't used
                try:
                    plan_json = json.loads(plan_text.strip())
                except json.JSONDecodeError:
                    raise ValueError("Empty or malformed JSON/text response from API.")
            else:
                # --- JSON PARSING ---
                json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', plan_text, re.IGNORECASE | re.DOTALL)
                
                if not json_match:
                    try:
                        plan_json = json.loads(plan_text.strip())
                    except json.JSONDecodeError:
                        raise ValueError("Could not extract or parse a valid JSON object from the API response.")
                else:
                    json_string = json_match.group(1)
                    plan_json = json.loads(json_string)

            # --- PROGRESSION TIP EXTRACTION ---
            progression_tip = self._extract_and_move_progression_tip(plan_json)
            
            # Convert JSON to enhanced Markdown for display
            plan_md = self._convert_plan_to_markdown_enhanced(plan_json)
            
            return {
                "success": True,
                "plan_json": plan_json,
                "plan_md": plan_md,
                "error": None,
                "progression_tip": progression_tip 
            }
            
        except Exception as e:
            # st.error(f"❌ Error generating plan: {str(e)}") # Removed Streamlit error call in class method
            return {
                "success": False,
                "plan_json": fallback_plan_json,
                "plan_md": self._convert_plan_to_markdown_enhanced(fallback_plan_json),
                "error": str(e),
                "progression_tip": progression_tip 
            }
    
    def _generate_fallback_plan_json(self, user_profile: Dict, day_name: str, day_focus: str, sets: str, reps: str, rest: str) -> Dict:
        """Generate simple fallback plan as a JSON object with required 3 warmup/cooldown items and correct steps, updated to the new schema."""
        
        exercise_count = int(self._determine_exercise_count(user_profile.get("session_duration", "30-45 minutes"), user_profile.get("fitness_level", "Level 3 – Moderate / Independent")))
        
        # Consistent steps for fallback
        wall_pushup_steps = [
            "Stand arm's length from a sturdy wall, placing hands shoulder-width and shoulder-height.",
            "Keeping your body straight, slowly bend your elbows to lean towards the wall.",
            "Pause briefly when your nose is close to the wall.",
            "Push through your palms to return to the straight-arm starting position."
        ]
        
        # Ensure 3-5 steps are formal and complete in the fallback
        base_exercises = [
            {
                "name": "Wall Push-ups (Incline)",
                "benefit": "Targets chest and arms safely.",
                "steps": wall_pushup_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Wall",
                "safety_cue": "Ensure feet are far enough back to feel a challenge in the chest and arms."
            },
            {
                "name": "Seated Overhead Press (Bodyweight)",
                "benefit": "Works the shoulders with back support.",
                "steps": [
                    "Sit tall on a sturdy chair, core lightly engaged.",
                    "Extend arms straight up towards the ceiling.",
                    "Slowly lower arms until elbows are level with shoulders.",
                    "Repeat the pressing motion, focusing on the shoulder muscles."
                ],
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Chair",
                "safety_cue": "Keep back firmly against the chair and avoid shrugging your shoulders excessively."
            },
            {
                "name": "Chair Squats (Assisted)",
                "benefit": "Targets lower body with joint support.",
                "steps": [
                    "Stand in front of a sturdy chair or bench, feet shoulder-width apart.",
                    "Push your hips back and slowly lower yourself, keeping your chest up and back straight.",
                    "Gently touch the chair with your glutes (do not fully sit or rest).",
                    "Push through your heels and mid-foot to stand back up, squeezing your glutes at the top."
                ],
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Chair",
                "safety_cue": "Keep knees tracking directly over your feet; do not let them cave inward."
            },
            {
                "name": "Modified Bird-Dog",
                "benefit": "Strengthens core and improves low-back stability.",
                "steps": [
                    "Start on hands and knees (tabletop position) with a neutral spine.",
                    "Lift one arm straight forward and the opposite leg straight back.",
                    "Hold briefly, keeping hips level and core tight to prevent rotation.",
                    "Slowly return to the start and switch sides."
                ],
                "sets": sets,
                "reps": f"{int(int(reps.split('-')[0]) / 2)}-{int(int(reps.split('-')[-1]) / 2)} / side",
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Yoga Mat",
                "safety_cue": "Move slowly and deliberately. Do not arch the lower back; keep the core engaged."
            }
        ]
        
        # Repeat/truncate base exercises to match the required count
        main_exercises = []
        for i in range(exercise_count):
            main_exercises.append(base_exercises[i % len(base_exercises)])
            
        # Fallback Warmup/Cooldown adjusted to new schema
        warmup = [
            {
                "name": "Arm Circles (Forward/Backward)",
                "benefit": "Shoulder mobility and light preparation.",
                "steps": wall_pushup_steps, # Reusing steps structure for compliance, though less ideal
                "sets": "1",
                "duration": "1 minute each direction",
                "intensity_rpe": "RPE 1-3",
                "rest": "15 seconds",
                "equipment": "Bodyweight",
                "safety_cue": "Maintain small, controlled circles to avoid shoulder strain."
            },
            {
                "name": "Seated Marching",
                "benefit": "Light cardio and lower body circulation.",
                "steps": wall_pushup_steps,
                "sets": "1",
                "duration": "2 minutes",
                "intensity_rpe": "RPE 1-3",
                "rest": "15 seconds",
                "equipment": "Chair",
                "safety_cue": "Keep back straight and focus on controlled, rhythmic movement."
            },
            {
                "name": "Torso Twists (Seated)",
                "benefit": "Spine rotation and core activation.",
                "steps": wall_pushup_steps,
                "sets": "1",
                "duration": "1 minute",
                "intensity_rpe": "RPE 1-3",
                "rest": "15 seconds",
                "equipment": "Chair",
                "safety_cue": "Twist gently from the core; do not force range of motion."
            }
        ]
        
        cooldown = [
            {
                "name": "Seated Hamstring Stretch", 
                "benefit": "Lengthens hamstrings for lower back relief.",
                "steps": wall_pushup_steps,
                "sets": "1",
                "hold": "60 seconds per leg", 
                "intensity_rpe": "RPE 1-3", 
                "rest": "15 seconds",
                "equipment": "Chair",
                "safety_cue": "Keep the spine long; only stretch until a gentle tension is felt."
            },
            {
                "name": "Seated Chest Stretch", 
                "benefit": "Opens chest and improves posture.",
                "steps": wall_pushup_steps,
                "sets": "1",
                "hold": "60 seconds", 
                "intensity_rpe": "RPE 1-3", 
                "rest": "15 seconds",
                "equipment": "Chair",
                "safety_cue": "Gently pull shoulder blades together; do not strain shoulders."
            },
            {
                "name": "Deep Diaphragmatic Breathing", 
                "benefit": "Calms the nervous system and aids muscle recovery.",
                "steps": wall_pushup_steps,
                "sets": "1",
                "hold": "2 minutes (slow, controlled breaths)", 
                "intensity_rpe": "RPE 1-3", 
                "rest": "15 seconds",
                "equipment": "Bodyweight",
                "safety_cue": "Breathe into your belly, not your chest. Keep shoulders relaxed."
            }
        ]

        return {
            "day_name": day_name,
            "warmup_duration": "5-7 minutes",
            "main_workout_category": f"Fallback Plan ({day_focus} Focus)",
            "cooldown_duration": "5-7 minutes",
            "warmup": warmup,
            "main_workout": main_exercises,
            "cooldown": cooldown,
            "safety_notes": [
                "This is a fallback plan due to API failure. Consult a professional before attempting.",
                "Progression Tip: If this plan felt easy, try to increase the set intensity by 1 RPE next time.",
                "Focus on perfect form rather than intensity.",
                "Hydrate before, during, and after the workout."
            ]
        }


# ============ CUSTOM CSS (NO CHANGE) ============
def inject_custom_css():
    """Inject custom CSS"""
    st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    .header-container {
        background: black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# ============ SESSION STATE (NO CHANGE) ============
def initialize_session_state():
    """Initialize session state"""
    if 'fitness_plan_generated' not in st.session_state:
        st.session_state.fitness_plan_generated = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {}
    if 'workout_plans' not in st.session_state:
        st.session_state.workout_plans = {}
    if 'generation_in_progress' not in st.session_state:
        st.session_state.generation_in_progress = False
    if 'form_submitted_and_validated' not in st.session_state:
        st.session_state.form_submitted_and_validated = False
    if 'all_prompts' not in st.session_state:
        st.session_state.all_prompts = {}
    if 'all_json_plans' not in st.session_state:
        st.session_state.all_json_plans = {}
    if 'all_progression_tips' not in st.session_state:
        st.session_state.all_progression_tips = {}

# ============ MAIN APPLICATION ============
def main():
    """Main application"""
    
    inject_custom_css()
    initialize_session_state()
    advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)
    
    # Header
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">💪 FriskaAI Fitness Coach </h1>
        <p class="header-subtitle">AI-Powered Personalized Fitness Plans</p>
    </div>
    """, unsafe_allow_html=True)
    
    # MAIN FORM
    if not st.session_state.fitness_plan_generated and not st.session_state.generation_in_progress:
        
        # BMI Placeholder initialization (CRITICAL for Instant Update)
        bmi_placeholder = st.empty()
        
        # --- Default/Current Values from Session State ---
        profile = st.session_state.user_profile
        
        # Calculate initial/re-run BMI for display in the placeholder
        current_weight_kg = profile.get('weight_kg', 70.0)
        current_height_cm = profile.get('height_cm', 170.0)
        current_bmi = 0
        if current_weight_kg > 0 and current_height_cm > 0:
            current_bmi = current_weight_kg / ((current_height_cm / 100) ** 2)
            bmi_placeholder.info(f"📊 Your BMI: {current_bmi:.1f}")
        else:
            bmi_placeholder.info("📊 Your BMI: Enter height and weight.")
        
        
        with st.form("fitness_form"):
            
            # Basic Info
            st.subheader("📋 Basic Information")
            col1, col2 = st.columns(2)
            
            # --- Form Inputs ---
            with col1:
                # Retrieve current state for sticky inputs
                name = st.text_input("Name *", placeholder="Your name", key="name_input", value=profile.get('name', ''))
                age = st.number_input("Age *", min_value=13, max_value=100, value=profile.get('age', 30), key="age_input")
                gender_default_index = ["Male", "Female", "Other"].index(profile.get('gender', 'Male'))
                gender = st.selectbox("Gender *", ["Male", "Female", "Other"], key="gender_input", index=gender_default_index)
            
            with col2:
                unit_system_default = profile.get('unit_system', 'Metric (kg, cm)')
                unit_system = st.radio("Units *", ["Metric (kg, cm)", "Imperial (lbs, in)"], key="unit_input", index=["Metric (kg, cm)", "Imperial (lbs, in)"].index(unit_system_default))
                
                weight_kg = 0.0
                height_cm = 0.0
                
                # --- REVISED: No callbacks inside the form ---
                if unit_system == "Metric (kg, cm)":
                    weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=profile.get('weight_kg', 70.0), key="weight_kg_input")
                    height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=profile.get('height_cm', 170.0), key="height_cm_input")
                else:
                    # Conversion for Imperial defaults
                    weight_lbs_default = profile.get('weight_kg', 70.0) / 0.453592
                    height_in_default = profile.get('height_cm', 170.0) / 2.54
                    
                    weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=weight_lbs_default, key="weight_lbs_input")
                    height_in = st.number_input("Height (in) *", min_value=39.0, max_value=98.0, value=height_in_default, key="height_in_input")
                    
                    weight_kg = weight_lbs * 0.453592
                    height_cm = height_in * 2.54
            
            # --- BMI Display Logic (This relies on Streamlit's full script rerun for update) ---
            final_bmi = 0
            if weight_kg > 0 and height_cm > 0:
                final_bmi = weight_kg / ((height_cm / 100) ** 2)
                # Update placeholder text with the most current value on the next rerun
                bmi_placeholder.info(f"📊 Your BMI: {final_bmi:.1f}")

            # Goals
            st.subheader("🎯 Fitness Goals")
            col1, col2 = st.columns(2)
            
            with col1:
                primary_goal_options = list(advisor.goal_programming_guidelines.keys())
                primary_goal_default_index = primary_goal_options.index(profile.get('primary_goal', 'General Fitness'))
                primary_goal = st.selectbox(
                    "Primary Goal *",
                    primary_goal_options, key="primary_goal_input", index=primary_goal_default_index
                )
            
            with col2:
                all_goals = ["None"] + list(advisor.goal_programming_guidelines.keys())
                secondary_goal_default_index = all_goals.index(profile.get('secondary_goal', 'None'))
                secondary_goal = st.selectbox(
                    "Secondary Goal (Optional)",
                    all_goals, key="secondary_goal_input", index=secondary_goal_default_index
                )
            
            # Fitness Level
            fitness_level_options = list(FITNESS_LEVELS.keys())
            fitness_level_default_index = fitness_level_options.index(profile.get('fitness_level', 'Level 3 – Moderate / Independent'))
            fitness_level = st.selectbox(
                "Fitness Level *",
                fitness_level_options, key="fitness_level_input", index=fitness_level_default_index
            )
            
            level_info = FITNESS_LEVELS[fitness_level]
            st.info(f"**{fitness_level}**: {level_info['description']} | RPE: {level_info['rpe_range']}")
            
            # Medical Conditions
            st.subheader("🏥 Health Screening")
            medical_conditions = st.multiselect(
                "Medical Conditions *",
                MEDICAL_CONDITIONS,
                default=profile.get('medical_conditions', ["None"]), key="medical_conditions_input"
            )
            
            # Physical Limitations
            st.warning("⚠️ **Physical Limitations** - Describe ANY injuries, pain, or movement restrictions")
            physical_limitations = st.text_area(
                "Physical Limitations (Important for Safety) *",
                placeholder="E.g., 'Previous right knee surgery - avoid deep squats'",
                height=100, key="physical_limitations_input", value=profile.get('physical_limitations', '')
            )
            
            # Training Schedule
            st.subheader("💪 Training Schedule")
            col1, col2 = st.columns(2)
            
            with col1:
                days_per_week = st.multiselect(
                    "Training Days *",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    default=profile.get('days_per_week', ["Monday", "Wednesday", "Friday"]), key="days_per_week_input"
                )
            
            with col2:
                session_duration_options = ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes"]
                session_duration_default_index = session_duration_options.index(profile.get('session_duration', '30-45 minutes'))
                session_duration = st.selectbox(
                    "Session Duration *",
                    session_duration_options, key="session_duration_input", index=session_duration_default_index
                )
            
            # Equipment
            st.subheader("🏋️ Available Equipment")
            eq_options = ["Bodyweight Only", "Dumbbells", "Resistance Bands", "Kettlebells", "Barbell", "Bench", "Pull-up Bar", "Yoga Mat", "Machines"]
            equipment = st.multiselect("Select all available equipment:", eq_options, default=profile.get('available_equipment', ["Bodyweight Only"]), key="equipment_input")

            if not equipment:
                equipment = ["Bodyweight Only"]
            
            # Submit button
            st.markdown("---")
            submit_clicked = st.form_submit_button(
                "🚀 Generate My Fitness Plan",
                use_container_width=True,
                type="primary"
            )
            
            # Process ONLY when button clicked
            if submit_clicked:
                # Validation: Check mandatory fields
                if not name or len(name.strip()) < 2:
                    st.error("❌ Please enter your name.")
                elif not days_per_week:
                    st.error("❌ Please select at least one training day.")
                elif final_bmi <= 0 or (weight_kg <= 0 or height_cm <= 0):
                    st.error("❌ Please ensure valid weight and height inputs.")
                else:
                    # Store profile and set flag to start generation
                    st.session_state.user_profile = {
                        "name": name.strip(),
                        "age": age,
                        "gender": gender,
                        "weight_kg": weight_kg,
                        "height_cm": height_cm,
                        "bmi": round(final_bmi, 1) if final_bmi > 0 else 0,
                        "primary_goal": primary_goal,
                        "secondary_goal": secondary_goal,
                        "fitness_level": fitness_level,
                        "medical_conditions": medical_conditions,
                        "physical_limitations": physical_limitations.strip(),
                        "days_per_week": days_per_week,
                        "session_duration": session_duration,
                        "available_equipment": equipment,
                        "unit_system": unit_system
                    }
                    
                    st.session_state.workout_plans = {} 
                    st.session_state.all_prompts = {}
                    st.session_state.all_json_plans = {}
                    st.session_state.all_progression_tips = {}
                    st.session_state.generation_in_progress = True
                    st.rerun()

    # =================================================================================
    # GENERATION BLOCK
    # =================================================================================
    if st.session_state.generation_in_progress:
        st.subheader("🔄 Generating your personalized fitness plan...")
        
        st.markdown("---")
        st.subheader("💡 LLM Prompts (For Debugging)")
        st.info("The text below is the *exact* prompt sent to the Mistral LLM for each day. This is for testing the safety and rule adherence.")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        profile = st.session_state.user_profile
        
        prompt_container = st.container()

        for idx, day in enumerate(profile['days_per_week']):
            
            previous_plans_to_pass = {d: st.session_state.workout_plans[d] for d in profile['days_per_week'] if d in st.session_state.workout_plans and profile['days_per_week'].index(d) < idx}
            
            system_prompt = advisor._build_system_prompt(
                profile, 
                day, 
                idx, 
                previous_plans_to_pass, 
                "Full Body"
            )
            
            st.session_state.all_prompts[day] = system_prompt
            
            with prompt_container:
                with st.expander(f"Prompt for **{day}** (Click to view)", expanded=False):
                    st.code(system_prompt, language='markdown')

            progress = (idx) / len(profile['days_per_week']) 
            if progress == 0 and idx == 0:
                 progress = 0.01
            progress_bar.progress(progress)
            status_text.text(f"Generating {day} workout... ({idx + 1}/{len(profile['days_per_week'])})")
            
            result = advisor.generate_workout_plan(
                profile,
                day,
                idx,
                previous_plans_to_pass, 
                "Full Body"
            )
            
            st.session_state.workout_plans[day] = result
            st.session_state.all_json_plans[day] = result.get('plan_json', None)
            st.session_state.all_progression_tips[day] = result.get('progression_tip', "No specific tip generated for this day.")
            
            progress_bar.progress((idx + 1) / len(profile['days_per_week']))


        progress_bar.empty()
        status_text.empty()
        
        all_success = all(
            st.session_state.workout_plans[day]['success'] 
            for day in profile['days_per_week']
        )
        
        if all_success:
            st.success("✅ Your fitness plan is ready! See the generated plan and the prompts below.")
        else:
            st.error("⚠️ Plan generation complete, but one or more days failed (used fallback). Check the API key and error messages in the console.")
        
        st.session_state.fitness_plan_generated = True
        st.session_state.generation_in_progress = False
        st.rerun() 
    
    # =================================================================================
    # DISPLAY PLANS
    # =================================================================================
    else:
        profile = st.session_state.user_profile
        
        st.markdown(f"👋 Welcome, **{profile.get('name', 'User')}**!")
        st.markdown(f"Your Personalized Fitness Plan is Ready")
        st.markdown(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 🎯 Goal: **{profile.get('primary_goal', 'N/A')}** | 💪 Level: **{profile.get('fitness_level', 'N/A')}**")
        
        st.markdown("\n")
        
        if profile.get('physical_limitations'):
            st.warning(f"⚠️ **Accommodated Limitations:** {profile['physical_limitations']}")
        
        st.markdown("---")
        
        # DEBUGGING PROMPT SECTION
        if st.session_state.all_prompts:
            st.markdown("## ⚙️ Debugging: LLM Prompts")
            with st.expander("Show Generated LLM Prompts (For Testing)", expanded=False):
                for day in profile['days_per_week']:
                    st.markdown(f"### Prompt for {day}")
                    st.code(st.session_state.all_prompts.get(day, "Prompt not stored."), language='markdown')
            st.markdown("---")
        
        # Display plans
        st.markdown("## 📅 Your Weekly Workout Schedule")
        
        for idx, day in enumerate(profile['days_per_week']):
            with st.expander(f"📋 {day} Workout", expanded=True if idx == 0 else False):
                if day in st.session_state.workout_plans:
                    plan_data = st.session_state.workout_plans[day]
                    
                    if plan_data['success']:
                        st.markdown(plan_data['plan_md'])
                    else:
                        st.error(f"⚠️ API Error: {plan_data.get('error', 'Unknown error')}. Showing fallback plan.")
                        st.markdown(plan_data['plan_md'])
                else:
                    st.warning("Plan not available")
        
        # Display consolidated Progression Tip
        st.markdown("---")
        st.markdown("## 📈 Weekly Progression Tip (CRITICAL FOR PROGRESS)")
        
        # Get the progression tip from the first successful day, or use the last one if all failed
        best_tip = next(
            (tip for day, tip in st.session_state.all_progression_tips.items() 
             if st.session_state.workout_plans.get(day, {}).get('success', False)),
            st.session_state.all_progression_tips.get(profile['days_per_week'][0], "Maintain current routine and focus on perfect form.")
        )
        st.success(f"**Your Focus for Next Week:** {best_tip}")
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.fitness_plan_generated = False
                st.session_state.workout_plans = {}
                st.session_state.user_profile = {}
                st.session_state.all_prompts = {}
                st.session_state.all_json_plans = {}
                st.session_state.all_progression_tips = {}
                st.rerun()
        
        with col2:
            markdown_content = generate_markdown_export(
                profile, 
                st.session_state.workout_plans,
                best_tip
            )
            st.download_button(
                label="📥 Download Plan (MD)",
                data=markdown_content,
                file_name=f"FriskaAI_Plan_{profile.get('name', 'User')}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col3:
             # Download JSON format
            json_export_data = {
                "profile": profile,
                "plans_json": st.session_state.all_json_plans
            }
            json_content = json.dumps(json_export_data, indent=4)
            st.download_button(
                label="⬇️ Download Plan (JSON)",
                data=json_content,
                file_name=f"FriskaAI_Plan_{profile.get('name', 'User')}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )

        
        # Additional Resources
        st.markdown("---")
        st.markdown("## 📚 Additional Resources")
        
        with st.expander("💡 Training Tips"):
            st.markdown("""
            **Maximizing Your Workout:**
            - **Warm-up is mandatory** - Never skip the warm-up to prevent injuries
            - **RPE Guide**: 
              - 3-4: Very light, can talk easily
              - 5-6: Moderate, breathing harder but can hold conversation
              - 7-8: Hard, difficult to talk
              - 9-10: Maximum effort
            - **Progressive Overload**: Gradually increase difficulty week by week
            - **Recovery**: Rest days are when muscles grow stronger
            - **Hydration**: Drink water before, during, and after workouts
            - **Form > Weight**: Perfect technique prevents injuries
            """)
        
        with st.expander("🍎 Nutrition Guidelines"):
            st.markdown(f"""
            **Based on your goal: {profile.get('primary_goal', 'N/A')}**
            
            {get_nutrition_guidelines(profile.get('primary_goal', 'General Fitness'))}
            
            **General Tips:**
            - Stay hydrated (8-10 glasses of water daily)
            - Eat protein within 2 hours post-workout
            - Balance macros: Protein, Carbs, Healthy Fats
            - Avoid processed foods and excessive sugar
            """)
        
        with st.expander("⚠️ Safety Warnings"):
            st.markdown("""
            **STOP EXERCISING if you experience:**
            - Chest pain or pressure
            - Severe shortness of breath
            - Dizziness or lightheadedness
            - Unusual fatigue
            - Sharp joint pain
            - Numbness or tingling
            
            **Important Notes:**
            - This plan is AI-generated guidance, NOT medical advice
            - Consult your doctor before starting any exercise program
            - Listen to your body and modify as needed
            - Keep emergency contacts readily available
            """)
        
        # FAQ Section
        display_faq()

def generate_markdown_export(profile: Dict, workout_plans: Dict, progression_tip: str) -> str:
    """Generate markdown file for download, including the progression tip. (NO CHANGE)"""
    
    md_content = f"""# FriskaAI Fitness Plan
## Generated on {datetime.now().strftime('%B %d, %Y')}

---

## 👤 Profile Summary

**Name:** {profile.get('name', 'User')}
**Age:** {profile.get('age', 'N/A')} | **Gender:** {profile.get('gender', 'N/A')} | **BMI:** {profile.get('bmi', 'N/A')}

**Primary Goal:** {profile.get('primary_goal', 'N/A')}
**Secondary Goal:** {profile.get('secondary_goal', 'None')}

**Fitness Level:** {profile.get('fitness_level', 'N/A')}
**Training Days:** {', '.join(profile.get('days_per_week', ['N/A']))}
**Session Duration:** {profile.get('session_duration', 'N/A')}

**Medical Conditions:** {', '.join(profile.get('medical_conditions', ['None']))}
**Physical Limitations:** {profile.get('physical_limitations', 'None')}

**Available Equipment:** {', '.join(profile.get('available_equipment', ['Bodyweight Only']))}

---

## 📈 Weekly Progression Goal
**Your Focus for Next Week:** {progression_tip}

---

"""
    
    # Add each workout day
    for day in profile.get('days_per_week', []):
        if day in workout_plans and workout_plans[day].get('plan_md'):
            status = "✅ SUCCESS" if workout_plans[day]['success'] else "⚠️ FALLBACK PLAN (API Error)"
            md_content += f"\n## {day} Workout - {status}\n\n"
            md_content += f"{workout_plans[day]['plan_md']}\n\n---\n"
    
    # Add footer
    md_content += """

## ⚠️ Important Disclaimers

1. This workout plan is AI-generated guidance and NOT a substitute for professional medical advice
2. Consult your physician before starting any new exercise program
3. Stop exercising immediately if you experience pain, dizziness, or unusual symptoms

---

**Generated by FriskaAI Fitness Coach**
"""
    
    return md_content

def get_nutrition_guidelines(goal: str) -> str:
    """Get nutrition guidelines based on goal (NO CHANGE)"""
    
    guidelines = {
        "Weight Loss": """
        - **Calorie Deficit**: Consume 300-500 calories below maintenance
        - **Protein**: 1.6-2.2g per kg bodyweight (preserves muscle)
        - **Carbs**: Moderate (prioritize around workouts)
        - **Fats**: 0.8-1g per kg bodyweight
        - **Meal Timing**: Eat protein with each meal
        """,
        "Muscle Gain": """
        - **Calorie Surplus**: Consume 200-400 calories above maintenance
        - **Protein**: 1.8-2.4g per kg bodyweight
        - **Carbs**: High (fuel for training and recovery)
        - **Fats**: 0.8-1.2g per kg bodyweight
        - **Post-Workout**: Protein + Carbs within 2 hours
        """,
        "Increase Overall Strength": """
        - **Balanced Calories**: Slight surplus or maintenance
        - **Protein**: 1.8-2.2g per kg bodyweight
        - **Carbs**: Moderate to high (power fuel)
        - **Pre-Workout**: Carbs for energy
        - **Recovery**: Focus on protein and sleep
        """,
        "Improve Cardiovascular Fitness": """
        - **Balanced Diet**: Maintenance calories
        - **Carbs**: Moderate to high (endurance fuel)
        - **Hydration**: Critical for performance
        - **Electrolytes**: Important for longer sessions
        - **Timing**: Light meal 2-3 hours before cardio
        """,
        "Rehabilitation & Injury Prevention": """
        - **Anti-Inflammatory Foods**: Omega-3s, berries, leafy greens
        - **Protein**: 1.6-2.0g per kg (tissue repair)
        - **Vitamin D & Calcium**: Bone health
        - **Collagen**: Consider supplementation
        - **Hydration**: Essential for joint health
        """,
        "Improve Flexibility & Mobility": """
        - **Hydration**: Essential for tissue elasticity and joint lubrication.
        - **Nutrient Rich**: Focus on vitamins and minerals for joint health.
        - **Magnesium**: May help with muscle relaxation.
        """,
        "Improve Posture and Balance": """
        - **Protein**: Adequate intake for muscle repair and core strength.
        - **Magnesium and Calcium**: Important for neuromuscular function.
        - **Ergonomics**: Pay attention to nutrition at your desk/workstation (e.g., proper seating).
        """
    }
    
    return guidelines.get(goal, """
    - **Balanced Approach**: Maintenance calories
    - **Protein**: 1.6-2.0g per kg bodyweight
    - **Carbs & Fats**: Balanced based on activity level
    - **Whole Foods**: Prioritize unprocessed options
    - **Consistency**: Key to long-term results
    """)

def display_faq():
    """Display FAQ section (NO CHANGE)"""
    st.markdown("---")
    st.markdown("## ❓ Frequently Asked Questions")
    
    faq_items = {
        "How often should I update my fitness level?": """
        Reassess every 4-6 weeks. Signs you've progressed:
        - Exercises feel easier at same intensity
        - Can complete more reps/longer duration
        - Recovery time has decreased
        """,
        
        "What if I miss a workout?": """
        Don't panic! Here's what to do:
        - **Missed 1 day**: Continue with next scheduled workout
        - **Missed 2-3 days**: Resume at lower intensity (80%)
        - **Missed >1 week**: Consider restarting at previous fitness level
        - Never "double up" to make up for missed sessions
        """,
        
        "Can I do the workouts at home?": """
        Absolutely! If you selected "Bodyweight Only" equipment, all exercises are home-friendly. 
        You can also modify equipment-based exercises with household items.
        """,
        
        "How long until I see results?": """
        Timeline varies by goal:
        - **Strength**: 2-4 weeks (neural adaptations)
        - **Muscle Growth**: 6-8 weeks (visible changes)
        - **Weight Loss**: 4-8 weeks (1-2 lbs/week is healthy)
        
        Consistency is key!
        """,
        
        "What if an exercise hurts?": """
        **STOP IMMEDIATELY.** Pain is your body's warning signal.
        
        Then:
        1. Assess: Sharp pain vs. muscle fatigue?
        2. Modify: Use easier variation or skip exercise
        3. Rest: Allow 24-48 hours recovery
        """,
        
        "Do I need supplements?": """
        Not required, but can help. **⚠️ ALWAYS consult doctor before starting supplements, especially with medical conditions.**
        """
    }
    
    for question, answer in faq_items.items():
        with st.expander(f"❔ {question}"):
            st.markdown(answer)

# ============ FOOTER ============
def display_footer():
    """Display footer with disclaimers (NO CHANGE)"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <h3>⚠️ Medical Disclaimer</h3>
        <p>
        <strong>This fitness plan is AI-generated guidance and NOT medical advice.</strong><br>
        Always consult with a qualified healthcare provider before starting any exercise program,<br>
        especially if you have pre-existing medical conditions or physical limitations.
        </p>
        <p>
        <strong>FriskaAI and its creators are not liable for any injuries or health complications<br>
        arising from the use of these workout plans.</strong>
        </p>
        <hr style='margin: 2rem 0;'>
        <p style='font-size: 0.9em;'>
        💪 <strong>FriskaAI Fitness Coach</strong> | Powered by AI<br>
        © 2025 | For educational and informational purposes only
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============ RUN APPLICATION ============
if __name__ == "__main__": 
    main()
    display_footer()