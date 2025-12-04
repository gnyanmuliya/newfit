import streamlit as st
import requests
from typing import Dict, List, Optional, Set, Any
import re
from datetime import datetime
import pandas as pd
import json
import numpy as np
import time

# ============ CONFIGURATION ============
# NOTE: The API key and Endpoint URL are set for an Azure Mistral deployment.
# API_KEY and ENDPOINT_URL are kept as provided.
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"
MAX_RETRIES = 3 

st.set_page_config(
    page_title="FriskaAI Fitness Coach",
    page_icon="💪",
    layout="wide"
)

# ============ FALLBACK MEDICAL CONDITIONS DATA ============
# This data is used if the Excel file cannot be loaded.
FALLBACK_MEDICAL_CONDITIONS_DATA = {
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
    },
    "Osteoarthritis": {
        "medications": "NSAIDs, Corticosteroids",
        "direct_impact": "Joint pain, reduced range of motion",
        "indirect_impact": "Stiffness, muscle weakness around affected joint",
        "contraindicated": "High-impact exercises (running, jumping), deep joint flexion/extension under heavy load.",
        "modified_safer": "Low-impact activities (swimming, cycling), isometric strengthening, short sessions."
    },
    "Chronic Lower Back Pain": {
        "medications": "Analgesics, muscle relaxants",
        "direct_impact": "Pain during movement, instability",
        "indirect_impact": "Fear avoidance, poor core endurance",
        "contraindicated": "Full spinal flexion (crunches), heavy lifting with rounded back, twisting under load.",
        "modified_safer": "Core stability (planks, bird-dog), walking, gentle stretching, bodyweight hip hinge."
    },
    "Other": {
        "medications": "N/A",
        "direct_impact": "Individualized risk factors",
        "indirect_impact": "N/A",
        "contraindicated": "Movements causing sharp pain or instability. High impact.",
        "modified_safer": "Consult doctor. Low-intensity, focus on stability and pain-free range of motion."
    }
}


# ============ LOAD EXCEL CONDITION DATABASE ============
@st.cache_data
def load_condition_database():
    """
    Load condition database from Excel file. Uses fallback data if the file is not found,
    ensuring the medical condition list remains populated.
    """
    condition_db = {}
    excel_loaded_successfully = False
    
    try:
        # CRITICAL: Assumes 'Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx' is accessible.
        df = pd.read_excel("C:\\Users\\gmuli\\Desktop\\new fit\\Top Lifestyle Disorders and Medical Conditions.xlsx")
        
        if 'Condition' in df.columns:
            for _, row in df.iterrows():
                condition_name = row['Condition']
                if pd.isna(condition_name) or str(condition_name).lower() == "none":
                    continue
                    
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
            excel_loaded_successfully = True

    except (FileNotFoundError, Exception) as e:
        # If file not found or another error, print error and load fallback
        st.error(f"Error loading Excel file: {e}. Using robust hardcoded fallback data.")
        condition_db = FALLBACK_MEDICAL_CONDITIONS_DATA
        excel_loaded_successfully = False

    return condition_db

# Load condition database
CONDITION_DATABASE = load_condition_database()

# ============ MEDICAL CONDITIONS LIST (Dynamically Generated) ============
# List for the UI multiselect: includes 'None' plus all conditions from the loaded Excel data OR fallback data.
# This fixes the issue of the dropdown being empty when the Excel file is missing.
MEDICAL_CONDITIONS_OPTIONS = ["None"] + sorted([c for c in CONDITION_DATABASE.keys() if str(c).lower() != 'none'])


# ============ FITNESS LEVELS WITH RPE ============
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

STATIC_HOLD_SCALING = {
    "Level 1 – Assisted / Low Function": "10-15 seconds",
    "Level 2 – Beginner Functional": "15-25 seconds",
    "Level 3 – Moderate / Independent": "25-45 seconds",
    "Level 4 – Active Wellness": "45-60 seconds",
    "Level 5 – Adaptive Advanced": "60-90 seconds",
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
        """Get condition details from loaded database. Uses fallback for common conditions if Excel fails."""
        if condition in CONDITION_DATABASE:
            return {k: v if v else 'N/A' for k, v in CONDITION_DATABASE[condition].items()}
        
        # NOTE: The general fallback logic for the prompt builder still exists for conditions not in the limited Excel data.
        # However, the UI now has the full list from the hardcoded FALLBACK_MEDICAL_CONDITIONS_DATA if Excel fails.
        return FALLBACK_MEDICAL_CONDITIONS_DATA.get(condition, {
            "medications": "Unknown",
            "direct_impact": "Use conservative approach",
            "indirect_impact": "Monitor for symptoms (e.g., fatigue, pain)",
            "contraindicated": "High-risk movements (e.g., heavy lifting, ballistic movements, full spinal flexion/extension) due to unknown risk.",
            "modified_safer": "Low-impact, controlled movements, seated or supported alternatives."
        })

    def _determine_split_focus_and_repetition(self, total_days: int, day_index: int, fitness_level: str) -> tuple[str, str]:
        """Determine the body part focus and the repetition rule for the current day based on complex rules."""
        
        days_map = {0: "Day 1", 1: "Day 2", 2: "Day 3", 3: "Day 4", 4: "Day 5", 5: "Day 6", 6: "Day 7"}
        current_day_label = days_map.get(day_index, f"Day {day_index + 1}")
        level_num = int(fitness_level.split(" – ")[0].replace('Level ', ''))
        
        default_focus = "Full Body Focus (Emphasis on major muscle groups)"
        
        if total_days == 1:
            focus = "Single Full-Body Workout"
            repetition_rule = "N/A (Single Session)"
        
        elif total_days == 2:
            focus = "Full Body Workout"
            if level_num <= 3:
                repetition_rule = "Exercises can be repeated from Day 1 (Full Body)."
            else:
                repetition_rule = "Exercises MUST be different from Day 1 (focus on variation for high levels)."
        
        elif total_days == 3:
            focus_map = {0: "Full Body (A)", 1: "Full Body (B)", 2: "Full Body (A)"}
            focus = focus_map.get(day_index % 3, default_focus)
            
            if level_num <= 2:
                 repetition_rule = "All exercises may be repeated from Day 1."
            elif day_index == 1:
                repetition_rule = "Workout B. Must be entirely different exercises from Day 1 (A)."
            elif day_index == 2:
                repetition_rule = "Workout A. Use SIMILAR muscle groups to Day 1, but DIFFERENT specific exercises/variations to avoid repetition."
            else:
                repetition_rule = "Workout A (Starting Point)."

        elif total_days == 4:
            focus_map = {0: "Upper Body (A) / Strength", 1: "Lower Body (B) / Stability", 2: "Upper Body (A) / Volume", 3: "Lower Body (B) / Endurance"}
            focus = focus_map.get(day_index % 4, default_focus)
            repetition_rule = "Split is A-B-A-B. Day 1 (A) and Day 3 (A) should have SIMILAR muscle groups but DIFFERENT specific exercises/variations. Day 2 (B) and Day 4 (B) follow the same rule."

        elif total_days == 5:
            focus_map = {0: "Upper Strength (A)", 1: "Lower Strength (B)", 2: "Full Body Endurance (C)", 3: "Upper Volume (A)", 4: "Lower Volume (B)"}
            focus = focus_map.get(day_index % 5, default_focus)
            repetition_rule = "Split is A-B-C-A-B. Workout A (Day 1 & 4) and B (Day 2 & 5) should use SIMILAR muscle groups but DIFFERENT specific exercises/variations. Workout C (Day 3) must be unique and endurance-focused."

        elif total_days == 6:
            focus_map = {0: "Push (A)", 1: "Pull (B)", 2: "Legs (C)", 3: "Push (A)", 4: "Pull (B)", 5: "Legs (C)"}
            focus = focus_map.get(day_index % 6, default_focus)
            repetition_rule = "Split is A-B-C-A-B-C. Use SIMILAR muscle groups but DIFFERENT exercises/variations for the repeated focus days (e.g., Push Day 1 vs Push Day 4)."

        elif total_days == 7:
            focus_map = {
                0: "Upper Strength (A)", 
                1: "Lower Strength (B)", 
                2: "Full Body Endurance (C)", 
                3: "Active Recovery/Mobility (D)",
                4: "Upper Volume (A)", 
                5: "Lower Volume (B)",
                6: "Core & Flexibility (E)"
            }
            focus = focus_map.get(day_index % 7, default_focus)
            repetition_rule = "Split is A-B-C-D-A-B-E. A, B, and C repeat with DIFFERENT exercises/variations on their second occurrence (Day 4/5). Day 3 (D) is Active Recovery. Day 6 (E) is unique."
            if current_day_label == days_map.get(3):
                focus = "Active Recovery Focus (Mobility, Stretching, Light Walk)"
        
        else:
             focus = default_focus
             repetition_rule = "Standard full body split."

        return focus, repetition_rule
    
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
        
        # Base count based on duration
        if total_minutes <= 25:
            count = 4
        elif total_minutes <= 40:
            count = 6
        elif total_minutes <= 55:
            count = 7
        else:
            count = 8
            
        # Adjustment based on fitness level
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
        with strict, numbered formatting for ALL sections.
        """
        if not plan_json:
            return "Plan structure is missing or empty."

        markdown_output = ""
        
        # Helper function for formatting exercise blocks
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
                set_label = "Sets" 
                set_value = exercise_data.get('sets', '1')
            elif section_type == 'cooldown':
                rep_label = "Hold Duration"
                rep_value = exercise_data.get('hold', 'N/A')
                set_label = "Sets"
                set_value = exercise_data.get('sets', '1')
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
        
        for idx, exercise in enumerate(plan_json.get('main_workout', [])):
            markdown_output += format_exercise_block(exercise, idx + 1, 'main')
        markdown_output += "---\n"
        
        # 3. Cool-Down
        markdown_output += f"## 🧘 **Cool-Down** ({plan_json.get('cooldown_duration', 'N/A')})\n\n"
        for idx, item in enumerate(plan_json.get('cooldown', [])):
            markdown_output += format_exercise_block(item, idx + 1, 'cooldown')
        markdown_output += "---\n"
        
        # 4. Safety Notes
        markdown_output += f"## 📝 **Safety and General Notes**\n"
        
        safe_notes = [note for note in plan_json.get('safety_notes', []) if not note.strip().lower().startswith("progression tip:")]
        
        if safe_notes:
            for idx, note in enumerate(safe_notes):
                markdown_output += f"**{idx + 1}.** {note}\n\n"
        else:
             markdown_output += "No specific safety notes provided for this session.\n\n"
        
        return markdown_output

    def _get_movement_pattern_from_exercise(self, exercise_name: str) -> str:
        """Heuristic function to classify an exercise by movement pattern."""
        name = exercise_name.lower()
        
        # PUSH Patterns
        if "push-up" in name or "press" in name or "chest" in name or "shoulder press" in name:
            if "overhead" in name or "military" in name or "vertical" in name:
                return "Vertical Push (Shoulders/Triceps)"
            return "Horizontal Push (Chest/Triceps)"

        # PULL Patterns
        if "row" in name or "pull-up" in name or "pulldown" in name or "rear delt" in name or "face pull" in name:
            if "vertical" in name or "pull-up" in name or "pulldown" in name:
                return "Vertical Pull (Back/Biceps)"
            return "Horizontal Pull (Back/Biceps)"
            
        # KNEE DOMINANT (Squat/Lunge)
        if "squat" in name or "lunge" in name or "step up" in name or "leg extension" in name or "quad" in name or "knee" in name:
            return "Knee Dominant (Quads/Glutes)"
            
        # HIP DOMINANT (Hinge)
        if "deadlift" in name or "hinge" in name or "glute bridge" in name or "hamstring" in name:
            return "Hip Dominant (Hamstrings/Glutes)"
            
        # CORE / STABILITY
        if "plank" in name or "crunch" in name or "sit-up" in name or "bicycle" in name or "bird-dog" in name or "core" in name or "twist" in name:
            if "rotation" in name or "twist" in name or "side" in name:
                return "Core Rotation/Anti-Lateral"
            if "plank" in name or "bird-dog" in name:
                return "Core Stability/Anti-Extension"
            return "Core Flexion/Extension"

        # ISOLATION
        if "curl" in name or "extension" in name or "raise" in name:
            if "bicep" in name:
                return "Bicep Isolation"
            if "tricep" in name:
                return "Tricep Isolation"
        
        # CARDIO / MOBILITY / OTHER
        if "walk" in name or "march" in name or "jog" in name or "run" in name or "mobility" in name or "stretch" in name or "circle" in name:
            return "Cardio/Mobility/Flexibility"

        return "Miscellaneous/Unknown Pattern"


    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        previous_plans: Dict, 
        workout_category: str = "Full Body"
    ) -> str:
        """
        Builds the entire system prompt based on the user's strict template,
        incorporating all demographic, split, location, and new repetition/duration/hold rules.
        """
        
        # --- DYNAMIC VALUE EXTRACTION ---
        name = user_profile.get("name", "User")
        age = user_profile.get("age", 30)
        bmi = user_profile.get("bmi", 22)
        gender = user_profile.get("gender", "Male")
        fitness_level = user_profile.get("fitness_level", "Level 3 – Moderate / Independent")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        equipment_list = user_profile.get("available_equipment", ["Bodyweight Only"])
        location = user_profile.get("workout_location", "Any") 
        medical_conditions = user_profile.get("medical_conditions", ["None"]) 
        
        # Determine programming targets
        level_data = FITNESS_LEVELS.get(fitness_level, FITNESS_LEVELS["Level 3 – Moderate / Independent"])
        target_rpe = level_data['rpe_range']
        target_sets = self.goal_programming_guidelines.get(primary_goal, {}).get('sets', '2-3')
        target_rest_desc = self.goal_programming_guidelines.get(primary_goal, {}).get('rest', '45-60 seconds')
        max_main_exercises = self._determine_exercise_count(user_profile.get("session_duration", "30-45 minutes"), fitness_level)
        total_days = len(user_profile.get("days_per_week", []))
        day_focus, repetition_rule = self._determine_split_focus_and_repetition(total_days, day_index, fitness_level) 
        
        # Level-based static hold duration
        current_level_hold = STATIC_HOLD_SCALING.get(fitness_level, STATIC_HOLD_SCALING["Level 3 – Moderate / Independent"])

        # Rep Range Safety Adjustment 
        target_reps = self.goal_programming_guidelines.get(primary_goal, {}).get('rep_range', '10-15')
        
        # Base safety reduction for low level/age/BMI 
        if fitness_level in ["Level 1 – Assisted / Low Function", "Level 2 – Beginner Functional"] or age >= 50 or bmi > 30:
             if '-' in target_reps:
                 low_rep = int(target_reps.split('-')[0])
                 target_reps = f"{max(low_rep, 8)}-{target_reps.split('-')[-1]}"
             elif int(target_reps.split('-')[-1]) > 12:
                 target_reps = f"10-{target_reps}"
        
        # Gender Adjustment
        if gender.lower() == "female" and fitness_level not in ["Level 1 – Assisted / Low Function", "Level 5 – Adaptive Advanced"]:
            if '-' in target_rpe:
                 rpe_low = int(target_rpe.split('-')[0])
                 rpe_high = int(target_rpe.split('-')[-1])
                 target_rpe = f"{rpe_low}-{max(rpe_high - 1, rpe_low)}"

        # --- REPETITION AVOIDANCE ---
        exercises_to_avoid = set()
        patterns_to_avoid = set()
        
        previous_training_days_keys = [d for d in user_profile.get('days_per_week', []) if user_profile.get('days_per_week', []).index(d) < day_index]
        days_to_check_patterns = previous_training_days_keys[-3:] 
        
        # Collect ALL exercise names for STRICT AVOIDANCE
        if previous_training_days_keys and previous_plans:
            for day_key in previous_training_days_keys:
                plan_data = previous_plans.get(day_key)
                if plan_data and plan_data.get('success') and 'plan_json' in plan_data and plan_data['plan_json']:
                    all_exercises = plan_data['plan_json'].get('main_workout', []) + \
                                    plan_data['plan_json'].get('warmup', []) + \
                                    plan_data['plan_json'].get('cooldown', [])
                    
                    for ex in all_exercises:
                        name = ex.get('name', '').strip()
                        if name:
                            exercises_to_avoid.add(name)

        # Collect MOVEMENT PATTERNS from the last 3 days
        if days_to_check_patterns and previous_plans:
            for day_key in days_to_check_patterns:
                plan_data = previous_plans.get(day_key)
                if plan_data and plan_data.get('success') and 'plan_json' in plan_data and plan_data['plan_json']:
                    all_exercises = plan_data['plan_json'].get('main_workout', []) 
                    
                    for ex in all_exercises:
                        name = ex.get('name', '').strip()
                        if name:
                            patterns_to_avoid.add(self._get_movement_pattern_from_exercise(name))
        
        exercises_to_avoid_list = list(exercises_to_avoid)
        patterns_to_avoid_list = [p for p in patterns_to_avoid if p not in ["Cardio/Mobility/Flexibility", "Miscellaneous/Unknown Pattern"]]
        # --- END REPETITION AVOIDANCE ---

        # --- RULE INJECTION - RESTRICTIONS (Section 3) ---
        allowed_equipment = ', '.join(equipment_list)
        
        # Fitness Level Constraint Logic (Rule 3.B)
        level_rules = {
            "Level 1 – Assisted / Low Function": "Choose supported or assisted exercises (e.g., wall squats, seated march, supported rows). Example substitution: Goblet Squat -> Wall Squat, Push-Up -> Wall Push-Up. STRICTLY AVOID standing balance challenges and unassisted core work.",
            "Level 2 – Beginner Functional": "Use low-impact, bodyweight-based functional exercises. Prioritize stability. Example substitution: Goblet Squat -> Chair Squat, Push-Up -> Incline Push-Up. STRICTLY AVOID advanced balance moves (unassisted lunges) or high-impact moves.",
            "Level 3 – Moderate / Independent": "Include moderate functional and resistance exercises. Example substitution: Goblet Squat -> Partial Squat, Push-Up -> Knee Push-Up. Introduce compound movements and light instability.",
            "Level 4 – Active Wellness": "Provide balanced strength, stability, and endurance training with varied equipment and moderate intensity/volume.",
            "Level 5 – Adaptive Advanced": "Offer full-intensity, functional, compound, and loaded stability movements. Use advanced resistance/techniques."
        }
        fitness_level_rules = level_rules.get(fitness_level, 'Balanced approach.')

        # Location and Equipment Rule 
        equipment_rule = f"WORKOUT LOCATION is {location}. Exercises MUST align with the environment. If 'Home', limit to bodyweight, dumbbells, bands, or TRX. If 'Gym', include machines, barbells, and cables. If 'Outdoor', prioritize walk, jog, step-ups, mobility drills, or bodyweight exercises."
        
        # Advanced Safety Avoidance (BMI/Age/Level Override)
        advanced_avoid_exercises = []
        safety_priority_note = ""
        
        if age >= 60:
            advanced_avoid_exercises.extend([
                "Heavy Compound Lifts", "High Impact Plyometrics", "Ballistic Movements"
            ])
            safety_priority_note = "AGE PRIORITY (≥ 60): Prioritize balance, mobility, and joint-friendly movements. Reduce overall volume and intensity."
        
        if bmi > 30:
            advanced_avoid_exercises.extend([
                "High Impact Jumps", "Fast Tempo/Ballistic Movements", "Deep Spinal Flexion/Extension"
            ])
            safety_priority_note += (" " if safety_priority_note else "") + "BMI PRIORITY (≥ 30): Emphasize low-impact exercises and gradual progression."
            
        # Combine medical restrictions and advanced safety notes
        medical_restrictions_list = []
        if medical_conditions and medical_conditions != ["None"]:
            for condition in medical_conditions:
                if condition != "None":
                    cond_data = self._get_condition_details_from_db(condition)
                    # Use cond_data.get('contraindicated', 'High-risk movements') which comes from Excel or fallback
                    medical_restrictions_list.append(f"CONDITION: {condition}. MUST AVOID: {cond_data.get('contraindicated', 'High-risk movements')}. PRIORITIZE: {cond_data.get('modified_safer', 'Low-impact alternatives')}.")
        
        if advanced_avoid_exercises:
             medical_restrictions_list.append(f"SAFETY OVERRIDE: Also AVOID: {', '.join(set(advanced_avoid_exercises))}. {safety_priority_note}")
        
        final_medical_restrictions = ' | '.join(medical_restrictions_list) if medical_restrictions_list else 'None.'

        # --- RULE INJECTION - STRUCTURE (Section 4) ---
        
        # Required Main Workout Categories
        required_structure = ""
        if day_focus.startswith("Full Body"):
             required_structure = "Main workout exercises MUST cover ALL 5 basic patterns: Push, Pull, Lower Body (Squat/Hinge/Lunge-variant), Core/Stabilization, and a Cardio/Mobility exercise."
        elif day_focus.startswith("Upper Body"):
             required_structure = "Main workout MUST emphasize Upper Body. It MUST include at least one PUSH and at least one PULL exercise."
        elif day_focus.startswith("Lower Body"):
             required_structure = "Main workout MUST emphasize Lower Body. It MUST include at least one Squat/Knee-Dominant movement and at least one Hinge/Hip-Dominant movement."
        else:
            required_structure = "Main workout must be balanced across all major movement patterns (Push, Pull, Core, Lower Body)."

        # Session Duration Breakdown
        duration_breakdown = "Warm-up: 10–15% | Main workout: 70–75% | Cooldown: 10–15%"

        # --- BUILD FINAL PROMPT STRING ---
        
        prompt_parts = [
            "You are FriskaAI, an ACSM-CEP certified clinical exercise physiologist. You MUST prioritize **maximum exercise variety** and **avoiding consecutive-day muscle group work**.",
            "Your ONLY output must be a single JSON object following the schema provided below.",
            "Never include text outside the JSON. Never add comments.",
            "",
            "# 1. JSON OUTPUT SCHEMA (MANDATORY)",
            json.dumps({
                "day_name": "string",
                "warmup_duration": "5-7 minutes",
                "main_workout_category": "string",
                "cooldown_duration": "5-7 minutes",
                "warmup": [
                    {
                        "name": "string",
                        "benefit": "string",
                        "steps": ["3-5 sequential, descriptive step strings"],
                        "sets": "1",
                        "duration": "string (e.g., 60 seconds total, or 30 seconds per side)",
                        "intensity_rpe": "RPE 1-3",
                        "rest": "15 seconds",
                        "equipment": "string",
                        "safety_cue": "string"
                    }
                ],
                "main_workout": [
                    {
                        "name": "string",
                        "benefit": "string",
                        "steps": ["3-5 sequential, descriptive step strings"],
                        "sets": target_sets,
                        "reps": target_reps, 
                        "intensity_rpe": f"RPE {target_rpe}",
                        "rest": target_rest_desc,
                        "equipment": "string",
                        "safety_cue": "string"
                    }
                ],
                "cooldown": [
                    {
                        "name": "string",
                        "benefit": "string",
                        "steps": ["3-5 sequential, descriptive step strings"],
                        "sets": "1",
                        "hold": "string (e.g., 30-60 seconds / side)",
                        "intensity_rpe": "RPE 1-3",
                        "rest": "15 seconds",
                        "equipment": "string",
                        "safety_cue": "string"
                    }
                ],
                "safety_notes": ["3-5 strings"]
            }, indent=2).replace('"', '`'),
            "",
            "# 2. USER PROFILE (DYNAMICALLY INJECTED)",
            json.dumps(user_profile, indent=2),
            "",
            "# 3. RESTRICTION RULES (DYNAMICALLY INJECTED)",
            f"- Current Day: **{day_name}** | Focus: **{day_focus}**",
            f"- Training Consistency Rule: **{repetition_rule}**", 
            f"- Equipment & Location Rule: **{equipment_rule}**. Strictly use only these equipment options: **{allowed_equipment}**", 
            f"- **STRICT EXERCISE NAME AVOIDANCE (All Previous Days):** DO NOT use these specific exercise names in ANY section: **{', '.join(exercises_to_avoid_list) if exercises_to_avoid_list else 'None'}**", 
            f"- **STRICT PATTERN AVOIDANCE (Recovery Constraint from last 3 days):** To ensure muscle group recovery and maximize variety, prioritize movements NOT listed here: **{', '.join(patterns_to_avoid_list) if patterns_to_avoid_list else 'None/Minor Muscle Groups Only'}**",
            f"- Fitness level constraints: **{fitness_level_rules}**", 
            f"- Medical and Safety Restrictions: **{final_medical_restrictions}**", 
            f"- Physical limitations: **{user_profile.get('physical_limitation', 'None')}**",
            "",
            "# 4. REQUIRED EXERCISE STRUCTURE",
            f"- Session Duration Breakdown: **{duration_breakdown}** (For pacing guidance)", 
            f"- Warmup: exactly 3 exercises",
            f"- Main workout: exactly {max_main_exercises} exercises. **All main exercises must be unique from each other and the warm-up/cool-down.**",
            f"- Cooldown: exactly 3 exercises",
            f"- Steps: always 3–5 **sequential, descriptive, and ACCURATE** steps for every exercise. **DO NOT HALLUCINATE** the steps.",
            f"- **Movement Balance Mandate:** {required_structure}",
            "",
            "# 5. SAFETY & GOAL MANDATES",
            f"- Intensity: Main workout RPE must be **{target_rpe}** | Warmup/Cooldown RPE must be **RPE 1-3**.",
            f"- **REPS vs DURATION RULE:** Main workout exercises MUST be in **Reps: {target_reps}** (e.g., 10-15) unless the exercise is a continuous cardiovascular activity.",
            f"- **STATIC HOLD SCALING:** All static holds (planks, stretches, stability drills) MUST use a hold time appropriate for the user's level, which is a maximum of **{current_level_hold}** total duration. For exercises requiring two sides (e.g., side plank, stretches), split the duration evenly.",
            f"- Reps/Sets: Main workout sets/reps must be **Sets: {target_sets}, Reps: {target_reps}**.",
            "- Never exceed user equipment.",
            "- Never use high-impact or unsafe movements (see restrictions in #3).",
            "- Prioritize stability for Level 1–2 and BMI > 30.",
            "- Safety Notes must include:",
            "   1. One top-priority safety tip for conditions/limitation.",
            "   2. One 'Progression Tip: ...' (Mandatory for next week's plan).",
            "   3. One or two general wellness tips.",
            "",
            "# 6. OUTPUT RULES",
            "- Output **only** valid JSON.",
            "- **NO** markdown outside the single ```json block.",
            "- **NO** text, explanation, or commentary.",
            "",
            "```json"
        ]
        
        return "\n".join(prompt_parts)
    
    def _extract_and_move_progression_tip(self, plan_json: Dict) -> str:
        """Extracts the mandatory progression tip and removes it from the daily notes."""
        progression_tip = "Maintain current routine and focus on perfect form."
        
        if 'safety_notes' in plan_json:
            new_notes = []
            for note in plan_json['safety_notes']:
                if note.strip().lower().startswith("progression tip:"):
                    progression_tip = note.strip().replace("Progression Tip:", "").strip()
                else:
                    new_notes.append(note)
            
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
        """
        Generate workout plan with fixed API call and JSON parsing, 
        including exponential backoff for resilience.
        """
        
        goal = user_profile.get("primary_goal", "General Fitness")
        target_sets = self.goal_programming_guidelines.get(goal, {}).get('sets', '3')
        target_reps = self.goal_programming_guidelines.get(goal, {}).get('rep_range', '12')
        target_rest = self.goal_programming_guidelines.get(goal, {}).get('rest', '60 seconds')
        
        total_days = len(user_profile.get("days_per_week", []))
        day_focus, _ = self._determine_split_focus_and_repetition(total_days, day_index, user_profile.get("fitness_level", "Level 3 – Moderate / Independent"))
        
        if user_profile.get("fitness_level") in ["Level 1 – Assisted / Low Function", "Level 2 – Beginner Functional"] or user_profile.get("age", 30) >= 50 or user_profile.get("bmi", 22) > 30:
             target_reps = "8-12" 
        
        fallback_plan_json = self._generate_fallback_plan_json(
            user_profile, 
            day_name, 
            day_focus,
            target_sets,
            target_reps,
            target_rest
        )
        
        progression_tip = "Maintain current routine and focus on perfect form."

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
                {"role": "system", "content": "You are FriskaAI, an expert clinical exercise physiologist. Your ONLY output is the JSON object requested by the user. Do not add any text or commentary outside the JSON."},
                {"role": "user", "content": system_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 4096
        }

        # --- EXPONENTIAL BACKOFF AND RETRY LOGIC ---
        error_message = ""
        for attempt in range(MAX_RETRIES):
            try:
                # 1. Make the API request
                response = requests.post(self.endpoint_url, headers=headers, json=payload)
                
                # 2. Check for successful status code
                if response.status_code != 200:
                    response_text = response.text
                    raise requests.HTTPError(f"API returned non-200 status: {response.status_code}. Response: {response_text[:100]}...")
                
                result = response.json()
                plan_text = result['choices'][0]['message']['content'] if 'choices' in result and result['choices'] else ""

                if not plan_text or len(plan_text) < 100:
                    raise ValueError("Empty or too short response from API")

                # 3. JSON Parsing and Validation - LOOK FOR THE ```json BLOCK
                json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', plan_text, re.IGNORECASE | re.DOTALL)
                
                if not json_match:
                    try:
                        plan_json = json.loads(plan_text.strip())
                    except json.JSONDecodeError:
                        raise ValueError("Could not extract or parse a valid JSON object from the API response.")
                else:
                    json_string = json_match.group(1)
                    plan_json = json.loads(json_string)

                # 4. Success: Extract tip and return
                progression_tip = self._extract_and_move_progression_tip(plan_json)
                plan_md = self._convert_plan_to_markdown_enhanced(plan_json)
                
                return {
                    "success": True,
                    "plan_json": plan_json,
                    "plan_md": plan_md,
                    "error": None,
                    "progression_tip": progression_tip 
                }

            except (requests.exceptions.RequestException, requests.HTTPError, ValueError, json.JSONDecodeError) as e:
                error_message = str(e)
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    pass

        # If all attempts fail, return the fallback plan with the final error message
        return {
            "success": False,
            "plan_json": fallback_plan_json,
            "plan_md": self._convert_plan_to_markdown_enhanced(fallback_plan_json),
            "error": error_message,
            "progression_tip": progression_tip 
        }
    
    def _generate_fallback_plan_json(self, user_profile: Dict, day_name: str, day_focus: str, sets: str, reps: str, rest: str) -> Dict:
        """Generate simple fallback plan as a JSON object with required structure."""
        
        exercise_count = int(self._determine_exercise_count(user_profile.get("session_duration", "30-45 minutes"), user_profile.get("fitness_level", "Level 3 – Moderate / Independent")))
        
        # Consistent steps for compliance
        generic_steps = [
            "Prepare your body and equipment for the movement.",
            "Execute the primary phase of the exercise with control.",
            "Hold or pause briefly at the point of maximum contraction/stretch.",
            "Return slowly to the starting position, maintaining tension and form.",
            "Repeat for the specified repetitions or duration."
        ]
        
        # Ensure 3-5 steps are formal and complete in the fallback
        base_exercises = [
            {
                "name": "Wall Push-ups (Incline)",
                "benefit": "Targets chest and arms safely.",
                "steps": generic_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Wall",
                "safety_cue": "Ensure feet are far enough back to feel a challenge in the chest and arms."
            },
            {
                "name": "Seated Band Rows (Pull)",
                "benefit": "Works the back and rear shoulders (Pull).",
                "steps": generic_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Resistance Band, Chair",
                "safety_cue": "Maintain a tall, upright posture throughout the pulling motion."
            },
            {
                "name": "Chair Squats (Assisted)",
                "benefit": "Targets lower body with joint support (Lower Body).",
                "steps": generic_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Chair",
                "safety_cue": "Keep knees tracking directly over your feet; do not let them cave inward."
            },
            {
                "name": "Modified Bird-Dog (Core/Stability)",
                "benefit": "Strengthens core and improves low-back stability.",
                "steps": generic_steps,
                "sets": sets,
                "reps": f"8-{int(int(reps.split('-')[-1]) / 2)} / side",
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Yoga Mat",
                "safety_cue": "Move slowly and deliberately. Do not arch the lower back; keep the core engaged."
            }
        ]
        
        main_exercises = []
        for i in range(exercise_count):
            main_exercises.append(base_exercises[i % len(base_exercises)])
            
        warmup = [
            {"name": "Arm Circles (Forward/Backward)", "benefit": "Shoulder mobility and light preparation.", "steps": generic_steps, "sets": "1", "duration": "1 minute each direction", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Bodyweight", "safety_cue": "Maintain small, controlled circles to avoid shoulder strain."},
            {"name": "Seated Marching", "benefit": "Light cardio and lower body circulation.", "steps": generic_steps, "sets": "1", "duration": "2 minutes", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Chair", "safety_cue": "Keep back straight and focus on controlled, rhythmic movement."},
            {"name": "Torso Twists (Seated)", "benefit": "Spine rotation and core activation.", "steps": generic_steps, "sets": "1", "duration": "2 minutes", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Chair", "safety_cue": "Twist gently from the core; do not force range of motion."}
        ]
        
        cooldown = [
            {"name": "Seated Hamstring Stretch", "benefit": "Lengthens hamstrings for lower back relief.", "steps": generic_steps, "sets": "1", "hold": "60 seconds per leg", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Chair", "safety_cue": "Keep the spine long; only stretch until a gentle tension is felt."},
            {"name": "Seated Chest Stretch", "benefit": "Opens chest and improves posture.", "steps": generic_steps, "sets": "1", "hold": "60 seconds", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Chair", "safety_cue": "Gently pull shoulder blades together; do not strain shoulders."},
            {"name": "Deep Diaphragmatic Breathing", "benefit": "Calms the nervous system and aids muscle recovery.", "steps": generic_steps, "sets": "1", "hold": "2 minutes (slow, controlled breaths)", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Bodyweight", "safety_cue": "Breathe into your belly, not your chest. Keep shoulders relaxed."}
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


# ============ CUSTOM CSS ============
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

# ============ SESSION STATE ============
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
        
        # BMI Placeholder initialization
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
            
            with col1:
                name = st.text_input("Name *", placeholder="Your name", key="name_input", value=profile.get('name', ''))
                age = st.number_input("Age *", min_value=13, max_value=100, value=profile.get('age', 30), key="age_input")
                gender_default_index = ["Male", "Female", "Other"].index(profile.get('gender', 'Male'))
                gender = st.selectbox("Gender *", ["Male", "Female", "Other"], key="gender_input", index=gender_default_index)
            
            with col2:
                unit_system_default = profile.get('unit_system', 'Metric (kg, cm)')
                unit_system = st.radio("Units *", ["Metric (kg, cm)", "Imperial (lbs, in)"], key="unit_input", index=["Metric (kg, cm)", "Imperial (lbs, in)"].index(unit_system_default))
                
                weight_kg = 0.0
                height_cm = 0.0
                
                if unit_system == "Metric (kg, cm)":
                    weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=profile.get('weight_kg', 70.0), key="weight_kg_input")
                    height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=profile.get('height_cm', 170.0), key="height_cm_input")
                else:
                    weight_lbs_default = profile.get('weight_kg', 70.0) / 0.453592 if profile.get('weight_kg') else 154.3
                    height_in_default = profile.get('height_cm', 170.0) / 2.54 if profile.get('height_cm') else 66.9
                    
                    weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=weight_lbs_default, key="weight_lbs_input")
                    height_in = st.number_input("Height (in) *", min_value=39.0, max_value=98.0, value=height_in_default, key="height_in_input")
                    
                    weight_kg = weight_lbs * 0.453592
                    height_cm = height_in * 2.54
            
            final_bmi = 0
            if weight_kg > 0 and height_cm > 0:
                final_bmi = weight_kg / ((height_cm / 100) ** 2)
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
            
            # Determine initial default selection: use saved profile or [] (empty) on first run
            initial_multiselect_default = profile.get('medical_conditions', [])
            
            medical_conditions = st.multiselect(
                "Medical Conditions *",
                MEDICAL_CONDITIONS_OPTIONS, # Now uses the list derived from loaded data or robust fallback
                default=initial_multiselect_default, 
                key="medical_conditions_input"
            )
            
            # Physical Limitations
            st.warning("⚠️ **Physical Limitations** - Describe ANY injuries, pain, or movement restrictions")
            physical_limitation = st.text_area( 
                "Physical Limitations (Important for Safety) *",
                placeholder="E.g., 'Previous right knee surgery - avoid deep squats'",
                height=100, key="physical_limitation_input", value=profile.get('physical_limitation', '')
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

            # Workout Location
            st.subheader("🗺️ Workout Location")
            location_options = ["Home", "Gym", "Outdoor", "Any"]
            location_default_index = location_options.index(profile.get('workout_location', 'Home'))
            workout_location = st.selectbox(
                "Where will you primarily work out?",
                location_options, key="location_input", index=location_default_index
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
                    # Cleanup medical conditions: If 'None' is selected along with others, remove 'None'.
                    if "None" in medical_conditions and len(medical_conditions) > 1:
                        medical_conditions.remove("None")
                    
                    if not medical_conditions:
                        medical_conditions = ["None"]
                    
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
                        "physical_limitation": physical_limitation.strip(),
                        "days_per_week": days_per_week,
                        "session_duration": session_duration,
                        "available_equipment": equipment,
                        "unit_system": unit_system,
                        "workout_location": workout_location
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
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        profile = st.session_state.user_profile

        # Prompt container/expander removed as requested for production deployment
        
        days_to_generate = profile.get('days_per_week', [])
        
        if not days_to_generate:
            st.error("Configuration error: Training days were not found in the profile. Please return to the form and select your training days.")
            st.session_state.generation_in_progress = False
            st.rerun() 
            return

        for idx, day in enumerate(days_to_generate):
            
            # Pass all previously generated plans to the prompt builder
            previous_plans_to_pass = {d: st.session_state.workout_plans[d] for d in days_to_generate if d in st.session_state.workout_plans and days_to_generate.index(d) < idx}
            
            # Building the system prompt, but NOT displaying it
            system_prompt = advisor._build_system_prompt(
                profile, 
                day, 
                idx, 
                previous_plans_to_pass, 
                "Full Body"
            )
            
            st.session_state.all_prompts[day] = system_prompt
            
            progress = (idx) / len(days_to_generate) 
            if progress == 0 and idx == 0:
                 progress = 0.01
            progress_bar.progress(progress)
            status_text.text(f"Generating {day} workout... ({idx + 1}/{len(days_to_generate)})")
            
            # Call the resilient plan generation function
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
            
            progress_bar.progress((idx + 1) / len(days_to_generate))


        progress_bar.empty()
        status_text.empty()
        
        all_success = all(
            st.session_state.workout_plans[day]['success'] 
            for day in days_to_generate
        )
        
        if all_success:
            st.success("✅ Your fitness plan is ready!")
        else:
            st.error("⚠️ Plan generation complete, but one or more days failed (used fallback). Check the API key and console logs for details.")
        
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
        
        if profile.get('physical_limitation'):
            st.warning(f"⚠️ **Accommodated Limitations:** {profile['physical_limitation']}")
        
        st.markdown("---")
        
        # DEBUGGING PROMPT SECTION REMOVED (As requested)
        
        # Display plans
        st.markdown("## 📅 Your Weekly Workout Schedule")
        
        for idx, day in enumerate(profile.get('days_per_week', [])):
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
        
        best_tip = next(
            (tip for day, tip in st.session_state.all_progression_tips.items() 
             if st.session_state.workout_plans.get(day, {}).get('success', False)),
            st.session_state.all_progression_tips.get(profile.get('days_per_week', [''])[0], "Maintain current routine and focus on perfect form.")
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
    """Generate markdown file for download, including the progression tip."""
    
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
**Physical Limitations:** {profile.get('physical_limitation', 'None')}

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
    """Get nutrition guidelines based on goal"""
    
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
    """Display FAQ section"""
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
    """Display footer with disclaimers"""
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