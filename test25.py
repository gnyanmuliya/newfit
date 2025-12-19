import streamlit as st
import requests
from typing import Dict, List, Optional, Set, Any
import re
from datetime import datetime
import pandas as pd
import json
import numpy as np
import time
import os # Import os for path handling
 # New import
import difflib # Import for fuzzy matching
 # Load environment variables immediately

# ============ CONFIGURATION ============
# NOTE: The API key and Endpoint URL are set for an Azure Mistral deployment.
# API_KEY and ENDPOINT_URL are kept as provided.
API_KEY = "uYlty4uFyTmjrb1TwAIS8a1Yxj39OB2R"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test01.westus.models.ai.azure.com/chat/completions"

if API_KEY == "ERROR_KEY_MISSING" or ENDPOINT_URL == "ERROR_URL_MISSING":
    st.error("Configuration Error: API Key or Endpoint URL not found. Please ensure your .env file is set up correctly.")
    
MAX_RETRIES = 3 
EXCEL_FILENAME = "Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx" # Standard filename
MET_FILENAME = "exercise_mets.json" # New JSON file

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
        "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing without control, High-Intensity Interval Training (HIIT) without medical clearance.Planks, Static Wall Sits, Isometric Holds > 5 sec, Valsalva maneuvers, Overhead lifting, Feet-elevated exercises.",
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
    }
    ,
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
    
    try:
        df = pd.read_excel(EXCEL_FILENAME) 
        
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
    
    except (FileNotFoundError, Exception) as e:
        # If file not found or another error, print error and load fallback
        st.error(f"Error loading {EXCEL_FILENAME}: {e}. Using robust hardcoded fallback data.")
        condition_db = FALLBACK_MEDICAL_CONDITIONS_DATA

    return condition_db

# ============ LOAD MET DATABASE (New Function) ============
@st.cache_data
def load_met_database():
    """
    Loads the MET values from the external JSON file.
    """
    try:
        # Attempt to open file. In the Canvas environment, files uploaded recently 
        # should generally be accessible in the root execution path.
        with open(MET_FILENAME, 'r') as f:
            met_db = json.load(f)
        return met_db
    except FileNotFoundError:
        st.warning(f"Warning: MET file '{MET_FILENAME}' not found. Using generic MET values for calorie calculation.")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"Error decoding MET JSON file: {e}. Cannot perform dynamic calorie calculation.")
        return {}


# Load databases
CONDITION_DATABASE = load_condition_database()
MET_DATABASE = load_met_database()

# ============ MEDICAL CONDITIONS LIST (Dynamically Generated) ============
# List for the UI multiselect: includes 'None' plus all conditions from the loaded Excel data OR fallback data.
MEDICAL_CONDITIONS_OPTIONS = ["None"] + sorted([c for c in CONDITION_DATABASE.keys() if str(c).lower() != 'none'])


# ============ FITNESS LEVELS REDEFINED ============
TRAINING_LEVELS = {
    "Beginner (0–6 months)": {
        "description": "New or detrained users with low motor control. Focus on strictly low-impact movements.",
        "rpe_range": "3-5",
        "rules": "Low-impact only. Prioritize mobility, stability, and support-based balance drills.",
        "met_key": "met_low",
        "allowed_examples": [
            "Chair squat", "Box squat", "Glute bridge", "Hip hinge drills",
            "Wall push-up", "Band rows", "Seated rows", "Marching", 
            "Step-ups", "Dead bug", "Bird dog", "Mobility drills"
        ],
        "excluded_exercises": [
            "Burpees", "Jumps", "Barbells", "Pistol squats", "HIIT", "Sprints"
        ]
    },
    "Intermediate (6 months–2 years)": {
        "description": "Users with foundational strength ready for moderate loading and progressive resistance.",
        "rpe_range": "5-7",
        "rules": "Focus on foundational strength, moderate loading, and conditioning. Avoid advanced plyometrics.",
        "met_key": "met_mod",
        "allowed_examples": [
            "Goblet squat", "Lunges", "Split squats", "DB RDL",
            "Incline push-up", "Full push-up", "Row variations", 
            "Jogging", "Light conditioning", "Planks", "Side planks"
        ],
        "excluded_exercises": [
            "Advanced plyometrics", "Heavy barbell work", "Olympic lifts"
        ]
    },
    "Advanced (2+ years)": {
        "description": "Highly trained individuals capable of maximizing intensity and handling heavy loads.",
        "rpe_range": "7-9",
        "rules": "Incorporate controlled power movements, heavy loading, and high-intensity intervals.",
        "met_key": "met_high",
        "allowed_examples": [
            "Loaded squats", "Weighted lunges", "Deadlifts", 
            "Pull-ups", "Dips", "Hanging core work", 
            "HIIT", "Sprints", "Controlled power movements"
        ],
        "excluded_exercises": [
            "Unsafe movements for specific conditions (seniors/medical)",
            "Olympic lifts (unless explicitly requested)"
        ]
    }
}

STATIC_HOLD_SCALING = {
    "Beginner (0–6 months)": "15-30 seconds",
    "Intermediate (6 months–2 years)": "30-60 seconds",
    "Advanced (2+ years)": "60-90 seconds",
}

# ============ GOAL OPTIONS ============
PRIMARY_GOALS = ["Weight Loss", "Weight gain", "Weight Maintenance"]
SECONDARY_GOALS = ["Increase Overall Strength", "Improve Cardiovascular Fitness", "Improve Flexibility & Mobility", "Rehabilitation & Injury Prevention", "Improve Posture & Balance"]


# ============ DYNAMIC CALORIE REFERENCE DATA (BASED ON WEIGHT) ============
# Base MET values scaled to Cal/min per 70kg (approximate for LLM reference)
BASE_CAL_PER_MIN_70KG = {
    "Low": 5.0,  
    "Moderate": 8.0, 
    "High": 13.0  
}

def _get_cal_reference(weight_kg: float) -> Dict[str, str]:
    """
    Calculates plausible Cal/min ranges based solely on weight, as the METs are now dynamic.
    """
    
    scaling_factor = weight_kg / 70.0
    
    cal_per_min = {
        "Low": BASE_CAL_PER_MIN_70KG["Low"] * scaling_factor,
        "Moderate": BASE_CAL_PER_MIN_70KG["Moderate"] * scaling_factor,
        "High": BASE_CAL_PER_MIN_70KG["High"] * scaling_factor
    }
    
    # Still provide MET guides, but ensure the LLM knows these are now dynamic/lookup based.
    def format_guide(value, met_label):
        low = int(max(1, value * 0.95))
        high = int(value * 1.05)
        return f"Dynamic {met_label} (Range: {low}-{high} Cal/min)"
        
    return {
        "Low_Guide": format_guide(cal_per_min["Low"], "Low MET"),
        "Moderate_Guide": format_guide(cal_per_min["Moderate"], "Moderate MET"),
        "High_Guide": format_guide(cal_per_min["High"], "High MET"),
        "Weight_KG": round(weight_kg, 1)
    }

# ============ GLOBAL HELPER FUNCTIONS FOR CALORIE CALCULATION ============

def parse_time_to_seconds(time_str: str) -> float:
    """Helper to parse time strings like '60-90 seconds' or '2 minutes' into average seconds."""
    if not time_str: return 0.0
    time_str = time_str.lower().strip()
    
    # Match seconds (e.g., 60-90 seconds or 45 seconds)
    sec_match = re.search(r'(\d+)\s*seconds', time_str)
    if sec_match:
        if '-' in time_str and len(time_str.split('-')[0]) < 4:
            low = int(re.search(r'(\d+)', time_str.split('-')[0]).group(1))
            high = int(re.search(r'(\d+)', time_str.split('-')[1]).group(1))
            return (low + high) / 2.0
        return int(sec_match.group(1))
    
    # Match minutes (e.g., 2 minutes)
    min_match = re.search(r'(\d+)\s*minutes', time_str)
    if min_match:
        return int(min_match.group(1)) * 60.0
    
    return 0.0

# Removed parse_llm_calories as it is no longer used.
# def parse_llm_calories(calorie_str: str) -> int:
#     """Extracts the integer calorie value from the LLM's 'Est: X Cal' string."""
#     # This function is now used to parse the Python-generated Calorie string (e.g., "Est: 100 Cal (MET: 5.5)")
#     match = re.search(r'Est: (\d+) Cal', calorie_str)
#     return int(match.group(1)) if match else 0

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
            "Weight gain": {
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
                "rep_range": "10-15 (for any resistance component)", # ENFORCING REPS for Main Workout
                "rest": "45-60 seconds (Active recovery or interval rest)",
                "sets": "2-3",
                "focus_type": "Cardio-respiratory endurance, interval training, low-impact."
            },
            "Improve Flexibility & Mobility": {
                "priority": "Emphasize stretching, joint mobility, dynamic range of motion, and breathing control. Focus on full ROM and static holds.",
                "rep_range": "8-12 (for controlled active mobility movements)", # ENFORCING REPS
                "rest": "30 seconds between sides",
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
                "rep_range": "10-15",
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
            },
            # Map new primary goals to guidelines
            "Weight Maintenance": {
                 "priority": "Balanced mix of strength and cardio for stable health.",
                "rep_range": "10-15",
                "rest": "45-60 seconds",
                "sets": "2-3",
                "focus_type": "Balanced, full-body circuit or supersets."
            }
        }

    def _get_met_value(self, exercise_name: str, fitness_level: str) -> float:
        """
        Looks up the dynamic MET value based on exercise name (cleaned) and user level, 
        using fuzzy matching as a fallback for robustness.
        """
        
        # Determine the correct MET key based on fitness level
        met_col_key = TRAINING_LEVELS.get(fitness_level, TRAINING_LEVELS["Beginner (0–6 months)"])['met_key']
        
        # Clean the exercise name to find a match in the MET database keys (e.g., "Wall Push-ups (Standard)" -> "wall_push_up")
        clean_name_base = re.sub(r'[\s\(\)-]+', '_', exercise_name.lower()).strip('_')
        
        # 1. Try finding a direct match
        for key, data in MET_DATABASE.items():
            if clean_name_base.startswith(key):
                return data.get(met_col_key, 3.0) # Default to 3.0 MET if level key is missing
        
        # 2. Apply Fuzzy Matching for robustness
        met_keys = list(MET_DATABASE.keys())
        
        # We look for the closest match in the MET database keys (cutoff threshold 0.7 for reasonable match)
        close_matches = difflib.get_close_matches(clean_name_base, met_keys, n=1, cutoff=0.7)
        
        if close_matches:
            best_match_key = close_matches[0]
            # Use the MET value for the closest matched exercise
            return MET_DATABASE[best_match_key].get(met_col_key, 3.0)
            
        # 3. Fallback based on activity type if no specific or fuzzy match is found
        if 'walk' in clean_name_base or 'march' in clean_name_base or 'stretch' in clean_name_base or 'mobility' in clean_name_base:
            return 1.5 # Low intensity fallback
        if 'squat' in clean_name_base or 'lunge' in clean_name_base or 'press' in clean_name_base or 'row' in clean_name_base:
            return 3.0 # Moderate intensity fallback
        if 'jump' in clean_name_base or 'run' in clean_name_base or 'burpee' in clean_name_base:
            return 6.0 # High intensity fallback
        
        return 3.0 # General safe fallback MET value

    
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

    def _calculate_calorie_rate(self, exercise_name: str, weight_kg: float) -> tuple[float, str]:
        """
        Determines the unit of effort (Rep/Sec) for logging based on exercise name.
        """
        name = exercise_name.lower()
        
        # Heuristic to determine if the input unit should be seconds
        is_time_based_warmup = any(unit in name for unit in ['march', 'jog', 'jack', 'run', 'cardio', 'walk', 'knees'])
        is_time_based_main = any(unit in name for unit in ["plank", "hold", "stretch", "mobility", "minute", "second", "breathing"])

        if is_time_based_warmup or is_time_based_main:
            unit_of_effort = "Sec"
        else:
            unit_of_effort = "Rep"
        
        # Return placeholder rate (1.0)
        return 1.0, unit_of_effort


    def _calculate_total_estimated_calories(self, exercise_data: Dict, weight_kg: float, fitness_level: str) -> str:
        """
        [FIX 2 Implementation] Calculates estimated calories using the MET lookup and the time duration.
        Crucially, this now calculates the burn for **ALL planned sets**, ensuring the JSON/MD export
        reflects the total estimated burn based on the full workout plan's volume (sets * reps/duration).
        Formula: Calories = (MET * Weight_KG * 3.5) / 200 * (Duration in minutes)
        """
        
        name = exercise_data.get('name', 'Unknown Exercise')
        
        # 1. Determine MET value based on fitness level and exercise name
        met_value = self._get_met_value(name, fitness_level)
        
        # 2. Determine Duration in Minutes
        sets_value = exercise_data.get('sets', '1')
        num_sets = 1
        try:
            num_sets = int(sets_value.split('-')[-1].strip()) if '-' in sets_value else int(sets_value.strip())
            num_sets = max(1, num_sets)
        except:
            pass

        # Determine total duration in seconds (units)
        section_key = 'main' # Assume main if not explicitly passed
        if exercise_data.get('warmup'): section_key = 'warmup'
        if exercise_data.get('cooldown'): section_key = 'cooldown'
        
        avg_units_per_set = 0.0
        
        reps_value = exercise_data.get('reps', '')
        hold_duration = exercise_data.get('hold', '')
        
        try:
            if section_key == 'cooldown':
                # Use hold duration in seconds (cooldown)
                avg_units_per_set = parse_time_to_seconds(hold_duration or '30 seconds')
            elif 'hold' in reps_value.lower() or 'minute' in reps_value.lower() or 'second' in reps_value.lower():
                 # Use reps value if it's an isometric hold time (in main workout/warmup)
                avg_units_per_set = parse_time_to_seconds(reps_value)
            elif section_key == 'warmup' and re.search(r'(\d+-\d+)', reps_value):
                 # For warm-up cardio, assume 90s (1.5 min) duration for calculation to keep it fast
                 if 'cardio' in name.lower() or 'march' in name.lower() or 'jack' in name.lower():
                     avg_units_per_set = 90.0 
                 else:
                     # For dynamic stretches (30s assumption)
                     avg_units_per_set = 30.0
            else:
                # Estimate duration for typical reps/sets in the main workout (5 seconds per rep is a decent approximation for strength)
                if '-' in reps_value:
                    low = int(re.search(r'(\d+)', reps_value.split('-')[0]).group(1))
                    high_part = reps_value.split('-')[-1]
                    high = int(re.search(r'(\d+)', high_part).group(1))
                    avg_reps = (low + high) / 2.0
                elif re.search(r'(\d+)', reps_value):
                    avg_reps = int(re.search(r'(\d+)', reps_value).group(1))
                else:
                    avg_reps = 10
                
                # Account for "per side"
                if 'side' in reps_value.lower() or 'each' in reps_value.lower():
                    avg_reps *= 2
                
                # Estimate time: 5 seconds per rep + 10 seconds transition
                avg_units_per_set = (avg_reps * 5) + 10 # seconds. This is the estimated duration of a SINGLE set in seconds.

        except Exception as e:
            # Fallback to a fixed 60 seconds duration per set on parsing error
            avg_units_per_set = 60.0
            
        # *** Calculate total time using ALL planned sets ***
        total_seconds = num_sets * avg_units_per_set
        total_minutes = total_seconds / 60.0

        # 3. Apply the Calorimetry Formula
        # Formula: Calories = (MET * Weight_KG * 3.5) / 200 * Minutes
        
        # Check for division by zero
        if weight_kg == 0 or total_minutes == 0:
            return "Est: 0 Cal (MET: 0.0)"

        estimated_calories = (met_value * weight_kg * 3.5) / 200 * total_minutes
        
        return f"Est: {round(estimated_calories)} Cal (MET: {met_value:.1f})" 

    def _determine_split_focus_and_repetition(self, total_days: int, day_index: int, fitness_level: str) -> tuple[str, str]:
        """Determine the body part focus and the repetition rule for the current day based on complex rules."""
        
        days_map = {0: "Day 1", 1: "Day 2", 2: "Day 3", 3: "Day 4", 4: "Day 5", 5: "Day 6", 6: "Day 7"}
        current_day_label = days_map.get(day_index, f"Day {day_index + 1}")
        # Note: Fitness level mapping is simplified due to 3 new tiers.
        
        default_focus = "Full Body Focus (Emphasis on major muscle groups)"
        
        if total_days == 1:
            focus = "Single Full-Body Workout"
            repetition_rule = "N/A (Single Session)"
        
        elif total_days == 2:
            focus = "Full Body Workout"
            if fitness_level == "Beginner (0–6 months)":
                repetition_rule = "Exercises can be repeated from Day 1 (Full Body)."
            else:
                repetition_rule = "Exercises MUST be different from Day 1 (focus on variation for high levels)."
        
        elif total_days == 3:
            focus_map = {0: "Full Body (A)", 1: "Full Body (B)", 2: "Full Body (A)"}
            focus = focus_map.get(day_index % 3, default_focus)
            
            if fitness_level == "Beginner (0–6 months)":
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
        if fitness_level == "Beginner (0–6 months)":
            # Max 4 exercises for Beginner, prioritizing very low volume.
            if count > 4:
                 count = 4 
        elif fitness_level == "Intermediate (6 months–2 years)":
             # Max 5 exercises for Intermediate, balancing stress and progress.
            if count > 5:
                count = 5 
        elif fitness_level == "Advanced (2+ years)":
             # Max 7 exercises for Advanced, allowing higher volume
            if count > 7:
                count = 7
            
        return str(count)

    def _convert_plan_to_markdown_enhanced(self, plan_json: Dict, profile: Dict) -> str:
        """
        [FIX 2 Implementation] Converts the structured JSON plan back into a user-friendly Markdown string 
        and calculates/stores the total planned units AND calls Python to calculate accurate calories 
        using the new MET lookup logic. This function ensures the `plan_json` object is updated 
        in-place with the correct calorie values before being saved to session state for export.
        """
        if not plan_json:
            return "Plan structure is missing or empty."

        markdown_output = ""
        total_calories_burned = 0
        weight_kg = profile.get('weight_kg', 70.0)
        fitness_level = profile.get('fitness_level', "Beginner (0–6 months)")
        
        # Helper function for formatting exercise blocks
        def format_exercise_block(exercise_data: Dict, index: int, section_type: str) -> str:
            nonlocal total_calories_burned
            
            name = exercise_data.get('name', 'Exercise Name Missing')
            benefit = exercise_data.get('benefit', exercise_data.get('focus', 'N/A'))
            steps = exercise_data.get('steps', [])
            
            # Initialize all variables used for calorie calculation and display
            reps_value = exercise_data.get('reps', 'N/A')
            hold_duration = exercise_data.get('hold', None)
            sets_value = exercise_data.get('sets', '1')
            rest_value = exercise_data.get('rest', '0 seconds')
            
            # Determine Rep/Duration/Hold label and value
            if section_type == 'main':
                if 'second' in reps_value.lower() or 'minute' in reps_value.lower() or 'max hold' in reps_value.lower():
                     rep_label = "Hold Duration"
                else:
                    rep_label = "Reps"
                rep_value_display = reps_value
                rest_value_display = rest_value
            elif section_type == 'warmup':
                rep_label = "Reps"
                # Use explicit time label for warm-up cardio (matching LLM prompt instruction)
                if index == 1 and ('march' in name.lower() or 'cardio' in name.lower() or 'jack' in name.lower() or 'knees' in name.lower()):
                     rep_label = "Reps (1-2 min equiv.)"
                rep_value_display = reps_value
                rest_value_display = rest_value
            elif section_type == 'cooldown':
                rep_label = "Hold Duration"
                rep_value_display = hold_duration or 'N/A'
                rest_value_display = rest_value
            else:
                rep_label = "Value"
                rep_value_display = "N/A"
                rest_value_display = "N/A"

            intensity_value = exercise_data.get('intensity_rpe', 'N/A').replace('RPE ', '')
            equipment = exercise_data.get('equipment', 'N/A')
            safety_cue = exercise_data.get('safety_cue', 'N/A')
            
            # --- CALORIE CALCULATION (PYTHON/MET-BASED) ---
            # Call the function to calculate the estimated calories for **ALL PLANNED SETS**
            calorie_calc_str = self._calculate_total_estimated_calories(
                {'name': name, 'sets': sets_value, 'reps': reps_value, 'hold': hold_duration, 'warmup': section_type=='warmup', 'cooldown': section_type=='cooldown'}, 
                weight_kg, 
                fitness_level
            )
            
            # Parse the Python-calculated calorie value and MET value
            estimated_calories_match = re.search(r'Est: (\d+) Cal', calorie_calc_str)
            met_match = re.search(r'MET: (\d+\.?\d*)', calorie_calc_str)
            
            estimated_calories_per_exercise = int(estimated_calories_match.group(1)) if estimated_calories_match else 0
            met_used = met_match.group(1) if met_match else '?'
            met_used_float = float(met_used) if met_match and met_match.group(1).replace('.', '', 1).isdigit() else 3.0 # Store MET as float

            total_calories_burned += estimated_calories_per_exercise
            calorie_burn_str = f"Est: {estimated_calories_per_exercise} Cal (MET: {met_used})"
                
            # --- PLANNED UNITS CALCULATION (CRITICAL FOR NEW CALC) ---
            # Recalculate units/set for logging defaults (should still be single set)
            num_planned_sets = 1
            avg_planned_units_per_set = 0.0
            
            try:
                # 1. Planned Sets (use the full sets value here only for the metadata storage, not for the calorie formula itself, which is already calculated above)
                num_planned_sets_total = int(sets_value.split('-')[-1].strip()) if '-' in sets_value else int(sets_value.strip())
                num_planned_sets_total = max(1, num_planned_sets_total) # Ensure non-zero
                
                # 2. Planned Units (Reps or Seconds) for ONE SET
                if section_type == 'cooldown':
                    avg_planned_units_per_set = parse_time_to_seconds(hold_duration or '30 seconds')
                elif rep_label == "Hold Duration":
                    avg_planned_units_per_set = parse_time_to_seconds(reps_value)
                elif index == 1 and section_type == 'warmup' and ('min equiv' in reps_value.lower() or 'minute' in reps_value.lower()):
                    avg_planned_units_per_set = 90.0 
                    
                else:
                    if '-' in reps_value:
                        low = int(re.search(r'(\d+)', reps_value.split('-')[0]).group(1))
                        high_part = reps_value.split('-')[-1]
                        high = int(re.search(r'(\d+)', high_part).group(1))
                        avg_reps = (low + high) / 2.0
                    elif re.search(r'(\d+)', reps_value):
                        avg_reps = int(re.search(r'(\d+)', reps_value).group(1))
                    else:
                        avg_reps = 10
                    
                    if 'side' in reps_value.lower() or 'each' in reps_value.lower():
                        avg_reps *= 2
                        
                    avg_planned_units_per_set = avg_reps

            except Exception as e:
                # Fallback to defaults on parsing error
                num_planned_sets_total = 1
                avg_planned_units_per_set = 10.0
            
            # Total Planned Units (for calculation rate use)
            # This is the total units (reps or seconds) across all planned sets
            planned_total_units = num_planned_sets_total * avg_planned_units_per_set

            # Store computed planned data for the performance calculation function
            # CRITICAL FIX: Ensure planned_total_cal is the multi-set value
            exercise_data['planned_sets_count'] = num_planned_sets_total # Total sets planned
            exercise_data['planned_units_per_set'] = avg_planned_units_per_set # Units per single set (used for logging input default)
            exercise_data['planned_total_units'] = planned_total_units # Total units across all sets (reps or seconds)
            exercise_data['planned_total_cal'] = estimated_calories_per_exercise # Correct multi-set total
            exercise_data['met_value'] = met_used_float 
            
            # --- CRITICAL FIX: Overwrite LLM's dummy value with Python's calculated value ---
            # This ensures the JSON export and the static MD reflect the accurate calorie calculation.
            exercise_data['est_calories'] = f"Est: {estimated_calories_per_exercise} Cal" 
            # ---------------------------------------------------------------------------------
            
            # Start of the strictly formatted output
            output = f"{index}. **{name}**\n\n"
            output += f"**Benefit:** {benefit}\n\n"
            output += "**How to Perform:**\n"
            
            if steps:
                output += "\n"
                for step_idx, step in enumerate(steps):
                    output += f"    {step_idx + 1}. {step.strip()}\n"
                output += "\n"
            else:
                 output += "    1. (Steps missing from plan - Follow general form)\n\n"
            
            output += f"**Sets:** {sets_value}\n\n"
            output += f"**{rep_label}:** {rep_value_display}\n\n"
            output += f"**Intensity:** RPE {intensity_value}\n\n"
            output += f"**Rest:** {rest_value_display}\n\n"
            output += f"**Equipment:** {equipment}\n\n"
            # FIX: Ensure safety_cue from the LLM's JSON is always displayed, even if it's 'N/A' from the LLM.
            # The fallback logic for the displayed markdown is removed here as the JSON should contain a value.
            output += f"**Safety Cue:** {safety_cue}\n\n"
            output += f"**Est. Calories Burned:** {calorie_burn_str}\n\n" # Python-calculated Calorie field
            
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
        
        # 4. Total Calories Summary
        markdown_output += f"## 🔥 **Daily Summary (Estimated)**\n\n"
        # NOTE: This summary now uses the aggregated estimated total from the Python calculation.
        markdown_output += f"**Total Est. Calories Burned for the Day:** **{total_calories_burned} Cal**\n\n"
        markdown_output += "---\n"

        # 5. Safety Notes
        markdown_output += f"## 📝 **Safety and General Notes**\n"
        
        safe_notes = [note for note in plan_json.get('safety_notes', []) if not note.strip().lower().startswith("progression tip:")]
        
        if safe_notes:
            for idx, note in enumerate(safe_notes):
                st.markdown(f"**{idx + 1}.** {note}\n")
        else:
            st.markdown("No specific safety notes provided for this session.")
        
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
        Builds the system prompt with strict safety enforcement, redundancy removal, 
        and explicit blocking of non-standard exercises based on user profile and day index.
        """
        print("user_profile:", user_profile)
        
        # --- DYNAMIC VALUE EXTRACTION ---
        name = user_profile.get("name", "User")
        age = user_profile.get("age", 30)
        bmi = user_profile.get("bmi", 22)
        gender = user_profile.get("gender", "Male")
        fitness_level = user_profile.get("fitness_level", "Beginner (0–6 months)") # UPDATED default
        primary_goal = user_profile.get("primary_goal", "Weight Maintenance") # UPDATED default
        target_body_parts = user_profile.get("target_body_parts", ["Full Body"])
        
        # NEW: Exercise avoidance field
        specific_avoidance = user_profile.get("specific_avoidance", "None")

        equipment_list = user_profile.get("available_equipment", ["Bodyweight Only"])
        location = user_profile.get("workout_location", "Any") 
        medical_conditions = user_profile.get("medical_conditions", ["None"]) 
        weight_kg = user_profile.get("weight_kg", 70.0) # CRITICAL: Get weight for LLM calc
        
        # Determine programming targets
        level_data = TRAINING_LEVELS.get(fitness_level, TRAINING_LEVELS["Beginner (0–6 months)"])
        target_rpe = level_data['rpe_range']

        # Get exclusions
        level_rules_text = level_data['rules'] 
        level_excluded_exercises = level_data.get('excluded_exercises', [])

        target_sets = self.goal_programming_guidelines.get(primary_goal, {}).get('sets', '2-3')
        target_rest_desc = self.goal_programming_guidelines.get(primary_goal, {}).get('rest', '45-60 seconds')
        max_main_exercises = self._determine_exercise_count(user_profile.get("session_duration", "30-45 minutes"), fitness_level)
        total_days = len(user_profile.get("days_per_week", []))
        day_focus, repetition_rule = self._determine_split_focus_and_repetition(total_days, day_index, fitness_level) 
        
        
        # Level-based static hold duration
        current_level_hold = STATIC_HOLD_SCALING.get(fitness_level, STATIC_HOLD_SCALING["Beginner (0–6 months)"])

        # Rep Range Safety Adjustment 
        target_reps = self.goal_programming_guidelines.get(primary_goal, {}).get('rep_range', '10-15')
        
        # Base safety reduction for low level/age/BMI 
        if fitness_level == "Beginner (0–6 months)" or age >= 50 or bmi > 30:
             if '-' in target_reps:
                 low_rep = int(target_reps.split('-')[0])
                 target_reps = f"{max(low_rep, 8)}-{target_reps.split('-')[-1]}"
             elif int(target_reps.split('-')[-1]) > 12:
                 target_reps = f"10-{target_reps}"
        
        special_population_rules = []

        # Gender Adjustment
        if gender.lower() == "female":
            if fitness_level == "Beginner (0–6 months)":
                special_population_rules.append("FEMALE BEGINNER: Avoid overly advanced upper-body progressions (e.g., standard push-ups from toes) immediately; start with incline or knee variations.")
            special_population_rules.append("Slightly reduce upper-body volume relative to lower body unless goal is specifically 'Weight gain'.")

        

        # ============ NEW STRICT LIMITATION LOGIC ============
        # Combine physical limitation text and medical conditions for keyword scanning
        limitation_text = user_profile.get('physical_limitation', '').lower()
        conditions_text = " ".join(medical_conditions).lower()
        combined_health_text = f"{limitation_text} {conditions_text}"

        # STRICT KNEE PAIN / INJURY / OSTEOARTHRITIS RULE
        if any(x in combined_health_text for x in ['knee', 'meniscus', 'acl', 'osteoarthritis', 'joint pain']):
            special_population_rules.append("🚨 **CRITICAL KNEE LIMITATION DETECTED** 🚨")
            special_population_rules.append("❌ **STRICTLY AVOID:** Lunges (forward/reverse/walking), Split Squats, Bulgarian Split Squats, Deep Squats, Pistol Squats, Jump Squats, Burpees, Running, Stair Intervals, High Impact movements.")
            special_population_rules.append("✅ **USE SAFE ALTERNATIVES:** Chair Squat or Partial Squat, Wall Squat (short range), Seated Leg Extension (unloaded), Standing Hip Abduction, Glute Bridge, Hip Hinge Drills, Seated March, Side Stepping.")
        
        # You can add similar blocks for Back Pain or Shoulder Pain here in the future
        if any(x in combined_health_text for x in ['back', 'spine', 'disc', 'lumbar']):
            special_population_rules.append("🚨 **BACK PAIN DETECTED** 🚨")
            special_population_rules.append("❌ **STRICTLY AVOID:** Sit-ups, Crunches, Superman (hyperextension), Heavy Overhead Press, Bent Over Rows (unsupported), High Impact.")
            special_population_rules.append("✅ **USE SAFE ALTERNATIVES:** Bird-Dog, Dead Bug, Plank (if tolerated), Glute Bridge, Chest Supported Row.")

        if any(x in combined_health_text for x in ['shoulder', 'rotator', 'impingement']):
            special_population_rules.append("🚨 **SHOULDER PAIN DETECTED** 🚨")
            special_population_rules.append("❌ **STRICTLY AVOID:** Overhead Press, Dips, Upright Rows, Full Push-ups (if painful).")
            special_population_rules.append("✅ **USE:** Floor Press, Lateral Raise (scaption), External Rotation, Band Pull-aparts.")

        if any(x in combined_health_text for x in ['wrist', 'carpal', 'forearm', 'hand']):
            special_population_rules.append("🚨 **WRIST PAIN DETECTED** 🚨")
            special_population_rules.append("❌ **STRICTLY AVOID:** Standard Push-ups (palms down), Dips, Planks on hands, Burpees, Front Squats, Heavy Pressing.")
            special_population_rules.append("✅ **USE:** Knuckle Push-ups (neutral wrist), Forearm Planks, Pulling exercises, Resistance Band Press.")

        population_constraints_str = " | ".join(special_population_rules) if special_population_rules else "Standard population rules apply."

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
            for day_key in previous_training_days_keys:
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
        level_rules = TRAINING_LEVELS[fitness_level]['rules']
        
        # FIX: Stronger Equipment Rule for Gym
        if location == "Gym" or "Full Gym Access" in equipment_list:
             equipment_rule = "WORKOUT LOCATION IS **GYM**. You MUST prioritize using **GYM SPECIFIC EQUIPMENT** (Machines, Cables, Barbells, Dumbbells) for the Main Workout. DO NOT simply generate a home workout. Use machines (e.g., Leg Press, Lat Pulldown) and cables."
        else:
             equipment_rule = f"WORKOUT LOCATION is {location}. Available Equipment: [{allowed_equipment}]. You must NOT hallucinate equipment. If 'Dumbbells' are not in the list, DO NOT generate dumbbell exercises. If 'Bodyweight Only' is selected, every exercise must be equipment-free."
        # Advanced Safety Avoidance (BMI/Age/Level Override)
        advanced_avoid_exercises = []
        safety_priority_note = ""

        special_population_rules = []

        if age >= 60:
            special_population_rules.append("AGE ≥ 60 DETECTED: Reduce impact and volume. Prioritize balance, stability, and joint-friendly movements.")
            special_population_rules.append("Select 'Beginner' or 'Intermediate' variations regardless of history unless explicitly requested.")
            special_population_rules.append("STRICTLY FORBIDDEN: Explosive movements (box jumps), high-risk spinal loading,Push-ups (regular, decline),Planks and side planks,Lunges & Bulgarian split squats,Squat jumps,Mountain climbers,Burpees,RDL, deadlift, barbell work,Resistance band rows,Any weighted variation,Any floor up-down transitions that may cause dizziness or BP spikes.")
            # Adjust RPE down slightly for safety
            if '-' in target_rpe:
                rpe_high = int(target_rpe.split('-')[-1])
                target_rpe = f"{target_rpe.split('-')[0]}-{max(rpe_high - 1, int(target_rpe.split('-')[0]) + 1)}"
        if bmi > 30:
            special_population_rules.append("BMI ≥ 30 DETECTED: Emphasize low-impact exercises to protect joints.")
            special_population_rules.append("Avoid frequent floor-to-standing transitions (keep exercises standing or seated/bench if possible).")
            special_population_rules.append("STRICTLY FORBIDDEN: Plyometrics, Jumps, Burpees.")
            special_population_rules.append("Focus on stability and step-wise progression.")
            special_population_rules.append("STRICTLY FORBIDDEN: Explosive movements (box jumps), high-risk spinal loading,Push-ups (regular, decline),Planks and side planks,Lunges & Bulgarian split squats,Squat jumps,Mountain climbers,Burpees,RDL, deadlift, barbell work,Resistance band rows,Any weighted variation,Any floor up-down transitions that may cause dizziness or BP spikes.")
            # Adjust RPE down slightly for safety
 
        # Combine medical restrictions and advanced safety notes
        medical_restrictions_list = []
        if medical_conditions and medical_conditions != ["None"]:
            for condition in medical_conditions:
                if condition != "None":
                    cond_data = self._get_condition_details_from_db(condition)
                    # STRONG LANGUAGE: "FORBIDDEN"
                    medical_restrictions_list.append(f"CONDITION: {condition} -> FORBIDDEN: {cond_data.get('contraindicated', 'High-risk moves')}. USE: {cond_data.get('modified_safer', 'Safe alternatives')}.")
        # New specific avoidance rule
        if specific_avoidance.lower() != "none" and specific_avoidance.strip():
             medical_restrictions_list.append(f"USER AVOIDANCE: Must avoid exercises involving or impacting: {specific_avoidance.strip()}.")
        
        if advanced_avoid_exercises:
             medical_restrictions_list.append(f"SAFETY OVERRIDE: Also AVOID: {', '.join(set(advanced_avoid_exercises))}. {safety_priority_note}")
        
        final_medical_restrictions = ' | '.join(medical_restrictions_list) if medical_restrictions_list else 'None.'

        # --- RULE INJECTION - STRUCTURE (Section 4) ---
        # --- INTERMEDIATE LEVEL ADJUSTMENT (FIX FOR "TOO ADVANCED") ---
        # ### NEW: Constraint for Intermediate to keep it grounded ###
        if fitness_level == "Intermediate (6 months–2 years)":
            level_rules_text += " DO NOT jump to advanced calisthenics or high-impact plyometrics. Focus on foundational strength with increased volume (sets/reps) or slight loading, not high complexity."
            
        # Required Main Workout Categories
        required_structure = ""
        target_body_parts_str = ', '.join(target_body_parts)
        
        if "Full Body" in target_body_parts:
             required_structure = "Main workout exercises MUST cover ALL 5 basic patterns: Push, Pull, Lower Body (Squat/Hinge/Lunge-variant), Core/Stabilization, and a Cardio/Mobility exercise."
        elif len(target_body_parts) > 1:
             required_structure = f"Main workout must efficiently train the specified body parts: {target_body_parts_str}. Ensure exercises target each selected area."
        elif target_body_parts == ["Upper Body"]:
             required_structure = "Main workout MUST emphasize Upper Body. It MUST include at least one PUSH and at least one PULL exercise."
        elif target_body_parts == ["Lower Body"]:
             required_structure = "Main workout MUST emphasize Lower Body. It MUST include at least one Squat/Knee-Dominant movement and at least one Hinge/Hip-Dominant movement."
        elif target_body_parts == ["Core"]:
             required_structure = "Main workout MUST exclusively focus on Core/Stability/Balance exercises."
        else:
            required_structure = "Main workout must be balanced across all major movement patterns (Push, Pull, Core, Lower Body)."

        # Session Duration Breakdown
        duration_breakdown = "Warm-up: 10–15% | Main workout: 70–75% | Cooldown: 10–15%"
        
        # --- BUILD FINAL PROMPT STRING ---
        
        # Removed calorie reference as it is calculated in Python
        
        prompt_parts = [
            "You are FriskaAI, an ACSM ,You are a certified fitness coach and corrective exercise specialist.. You MUST prioritize **maximum exercise variety** and **avoiding consecutive-day muscle group work**.",
            "Your ONLY output must be a single JSON object following the schema provided below.",
            "Never include text outside the JSON. Never add comments.",
            "",
            "# 1. JSON OUTPUT SCHEMA (MANDATORY)",
            json.dumps({
                "day_name": "string",
                "warmup_duration": "5-7 minutes",
                # [UPDATE 1]: Changed description to encourage clearer non-jargon titles.
                "main_workout_category": "string (Example: Upper Body Strength, Full Body Circuit, Lower Body Endurance, Core Stability. Use clear, descriptive non-jargon terms)",
                    "cooldown_duration": "5-7 minutes",
                    "warmup": [
                    {
                        "name": "string",
                        "benefit": "string",
                        "steps": ["3-5 sequential, descriptive step strings"],
                        "sets": "1",
                        "reps": "string (e.g., 10-15)",
                        "intensity_rpe": "RPE 1-3",
                        "rest": "15 seconds",
                        "equipment": "string",
                        # LLM MUST ONLY PROVIDE A DUMMY VALUE/FORMAT. PYTHON WILL REPLACE THIS WITH ACCURATE CALCULATION.
                        "est_calories": "Est: 0 Cal (MET: 0.0)",
                        "safety_cue": "string (Mandatory: Provide a specific form tip or safety point for THIS exercise)" # REINFORCED MANDATE
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
                         # LLM MUST ONLY PROVIDE A DUMMY VALUE/FORMAT. PYTHON WILL REPLACE THIS WITH ACCURATE CALCULATION.
                        "est_calories": "Est: 0 Cal (MET: 0.0)",
                        "safety_cue": "string (Mandatory: Provide a specific form tip or safety point for THIS exercise)" # REINFORCED MANDATE
                    }
                ],
                "cooldown": [
                    {
                        "name": "string",
                        "benefit": "string",
                        "steps": ["3-5 sequential, descriptive step strings"],
                        "sets": "1",
                        "reps": "string (e.g., 30-60 seconds / side)",
                        "intensity_rpe": "RPE 1-3",
                        "rest": "15 seconds",
                        # LLM MUST ONLY PROVIDE A DUMMY VALUE/FORMAT. PYTHON WILL REPLACE THIS WITH ACCURATE CALCULATION.
                        "equipment": "string",
                        "est_calories": "Est: 0 Cal (MET: 0.0)",
                        "safety_cue": "string (Mandatory: Provide a specific form tip or safety point for THIS exercise)" # REINFORCED MANDATE
                    }
                ],
                "safety_notes": ["3-5 strings"]
            }, indent=2).replace('"', '`'),
            "",
            "# 2. USER PROFILE (DYNAMICALLY INJECTED)",
            json.dumps(user_profile, indent=2),
            f"- Targeted Body Parts: **{target_body_parts_str}**", # NEW: Target body part instruction
            "",
            "# 3. RESTRICTION RULES (DYNAMICALLY INJECTED)",
            # ... [Previous parts of prompt list] ...

            # 3. RULES & CONSTRAINTS (General)
            f"- **Fitness Level Constraints:** {level_rules_text}",
            f"- **FORBIDDEN MOVES (Level-Specific):** You MUST NOT use these exercises: {' '.join(level_excluded_exercises)}.",
            f"- **RECOMMENDED MOVES:** Prioritize these exercises: {' '.join(level_rules)}.",
            f"- **Training Consistency Rule:** {repetition_rule}", 
            f"- **Equipment & Location Rule:** {equipment_rule}. Strictly use only these equipment options: {allowed_equipment}. Not available equipment MUST NOT be included (e.g., resistance bands if not listed, no exercise using bands).", 
            f"- **STRICT EXERCISE NAME AVOIDANCE (All Previous Days):** DO NOT use these specific exercise names in ANY section: {', '.join(exercises_to_avoid_list) if exercises_to_avoid_list else 'None'}", 
            f"- **STRICT PATTERN AVOIDANCE (Recovery Constraint from last 3 days):** To ensure muscle group recovery and maximize variety, prioritize movements NOT listed here: {', '.join(patterns_to_avoid_list) if patterns_to_avoid_list else 'None/Minor Muscle Groups Only'}",
            f"- **EXPLICITLY BANNED:** Do NOT use 'Seated Hip Rotation', 'Seated Hip Circles', or any non-standard/made-up exercise.",
            "",
            # 4. CRITICAL SAFETY OVERRIDES (HIGHEST PRIORITY)
            "### CRITICAL SAFETY OVERRIDES & MEDICAL MANDATES",
            f"- **PRIMARY MANDATE:** These restrictions OVERRIDE all other instructions. If an exercise contradicts these, you must NOT use it.",
            f"- **Active Medical Conditions:** {final_medical_restrictions}",
            f"- **User-Defined Physical Limitations:** {user_profile.get('physical_limitation', 'None')}",
            f"- **Population Constraints:** {population_constraints_str}",
            f"- **General Safety Rule:** If there is any physical limitation/medical condition, PRIORITIZE safety and AVOID aggravating movements (e.g., for knee pain, avoid lunges/split squats/deep squats/jumps/running).",
            f"- **Age/BMI Rule:** If Age>=60 or BMI>30, PRIORITIZE low-impact, joint-friendly exercises and AVOID high-risk movements. Give easier versions of push-ups/planks/lunges/squats/deadlifts (e.g., incline push-ups, wall push-ups, glute bridges instead of deadlifts).",
            
            # Explicit logic for the AI to process the limitation text
            f"- **CONSTRAINT ENFORCEMENT LOGIC:**",
            f"  1. If limitation mentions **'knee'**: STRIKE OUT all Lunges, Deep Squats, Jump Squats, Kneeling exercises.",
            f"  2. If limitation mentions **'back'**: STRIKE OUT Sit-ups, Crunches, Superman, Heavy Overhead Press.",
            f"  3. If limitation mentions **'shoulder'**: STRIKE OUT Overhead Press, Dips, Upright Rows.",
            f"  4. If limitation mentions **'hypertension'** or **'BP'**: STRIKE OUT Planks, Isometric Holds, Feet-Elevated moves.",
            
            # Context for the day
            f"- **Context:** Current Day: **{day_name}** | Fitness Level/Experience: **{fitness_level}**", 
            "",
            "# 5.0 REQUIRED EXERCISE STRUCTURE",
            f"- Session Duration Breakdown: **{duration_breakdown}** (For pacing guidance)", 
            f"- Warmup: exactly 3 exercises. MUST use the **'reps'** field for dynamic movements, not 'duration'.",
            f"- **Warmup Structure Mandate (CRITICAL VARIATION):** The 3 exercises MUST follow this order and focus. If any exercises are performed in both side (left/right) then it should show either sec/side or rep/side in reps. Exercise names MUST be varied across different training days (e.g., use Cat-Cow Stretch, Seated Glute Stretch, or Wall Chest Stretch instead of generic 'Stretch'). **AVOID repeating:** Arm Circles, Standing Hip Swings, Low-Impact High Knees, Scapular Push-Ups, Thoracic Rotations.",
            "   1. Cardio Type Exercise (e.g., Low-Impact High Knees, Modified Jumping Jacks, Spot Walking/Marching). This exercise MUST account for **90 seconds (1.5 minutes)** of the total duration. The duration MUST be used in the calorie calculation.",
            "   2. Upper Body Dynamic Stretch/Mobility. The duration for this should be treated as **10-15 reps** for calculation.",
            "   3. Lower Body Dynamic Stretch/Mobility. The duration for this should be treated as **10-15 reps** for calculation.",
            f"- Cooldown: exactly 3 static stretches/exercises. Exercises/Static Stretches MUST relate to the main workout. The duration for this should be treated as **15-30 sec**. If any exercises are performed in both side (left/right) then it should show either sec/side or rep/side in reps. Exercise names MUST be varied across different training days. **AVOID repeating:** (same exercises) (e.g. Seated Glute Stretch, Wall Chest Stretch, Deep Diaphragmatic Breathing, Standing Quad Stretch, Hamstring Floor Stretch, shoulder static stretch)",
            f"- Main workout: exactly {max_main_exercises} exercises. **All main exercises must be unique from each other and the warm-up/cool-down.**",
            "- **STRICT EXERCISE NAMING:** Use ONLY standard, recognized kinesiology terms. **DO NOT INVENT** exercises (e.g., 'Seated Hip Circles' is invalid -> use 'Seated Hip Internal/External Rotation' or 'Seated March').",
            f"- **Movement Focus Mandate:** {required_structure}", 
            "",
            "# 5.1 SUBSTITUTION & SAFETY PROTOCOL (MANDATORY)",
            "- **SUBSTITUTION RULE:** If an exercise is contraindicated by a medical condition, too advanced (e.g., jumps for BMI>30/Age>60), or requires unavailable equipment, you MUST downgrade it.",
            "- **FORMAT:** If you substitute an exercise, you MUST fill the `substitution_note` field in JSON with: 'Replaced [Original Exercise] with [New Exercise] because [Reason (e.g., too advanced / unsafe / equipment unavailable)].'",
            "- **SAFETY CUES:** Every exercise MUST have a `safety_cue` specific to the user's constraints (e.g., 'Perform slowly to protect knees').",
            "",
            "# 6. SAFETY & GOAL MANDATES (CRITICAL CALORIE GUIDANCE)",
            f"- Intensity: Main workout RPE must be **{target_rpe}** | Warmup/Cooldown RPE must be **RPE 1-3**.",
            "- **IMPORTANT:** The Calorie (MET) calculation is handled externally by a Python function. Focus solely on generating highly relevant and safe exercise routines according to the rules above. Use a default 'Est: 0 Cal (MET: 0.0)' in your JSON output for the `est_calories` field.",
            f"- **CRITICAL MANDATE: SAFETY CUE:** Every single exercise object (warmup, main, cooldown) MUST include a specific and concise instruction in the `safety_cue` field related to form, balance, or injury prevention for that particular exercise. DO NOT leave it blank.", 
            f"- **STRICT MAIN WORKOUT REPS RULE (Standard):** All Main workout exercises MUST be in **Reps: {target_reps}** (e.g., 10-15). **DO NOT** use a 'duration' or 'hold' field in the 'main_workout' section for non-isometric exercises.",
            f"- **SPECIAL ISOMETRIC REPS RULE (Plank/Wall Sit):** For static holds (like Plank, Wall Sit) in the **main_workout** section, the 'reps' field MUST represent the hold time, for example: '**30-45 seconds (or max hold)**'.",
            f"- **BI-LATERAL REPS CLARIFICATION:** For any exercise performed one side at a time (e.g., Lunges, Single-Arm Row, Side Plank), the 'reps' value MUST clearly indicate per side (e.g., '10-12 / side' or '10-12 each leg').",
            f"- **STATIC HOLD SCALING:** All static holds (planks, stretches, stability drills) MUST use a hold time appropriate for the user's level, which is a maximum of **{current_level_hold}** total duration. For exercises requiring two sides (e.g., side plank, stretches), split the duration evenly.",
            f"- Reps/Sets: Main workout sets/reps must be **Sets: {target_sets}, Reps: {target_reps}**.",
            "- Never exceed user equipment.",
            "- Prioritize stability for Beginner level users and BMI > 30.",
            "- Safety Notes must include:",
            "   1. One top-priority safety tip for conditions/limitation.",
            "   2. One 'Progression Tip: ...' (Mandatory for next week's plan).",
            "   3. One or two general wellness tips.",
            "",
            "# 6. OUTPUT RULES",
            "- Output **only** valid JSON.",
            "- **NO** markdown outside the single ```json block.",
            "- **NO** text, explanation, or commentary.",
            "",
            "```json"
        ]
        
        print("prompt_parts","\n".join(prompt_parts))

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
        
        goal = user_profile.get("primary_goal", "Weight Maintenance")
        target_sets = self.goal_programming_guidelines.get(goal, {}).get('sets', '3')
        target_reps = self.goal_programming_guidelines.get(goal, {}).get('rep_range', '12')
        target_rest = self.goal_programming_guidelines.get(goal, {}).get('rest', '60 seconds')
        
        total_days = len(user_profile.get("days_per_week", []))
        day_focus, _ = self._determine_split_focus_and_repetition(total_days, day_index, user_profile.get("fitness_level", "Beginner (0–6 months)"))
        
        if user_profile.get("fitness_level") == "Beginner (0–6 months)" or user_profile.get("age", 30) >= 50 or user_profile.get("bmi", 22) > 30:
             target_reps = "8-12" 
        
        # [FIX 2 Implementation Note] Generate fallback JSON using the dummy calorie value
        # This plan will still be passed through _convert_plan_to_markdown_enhanced, 
        # where the actual calorie calculation will overwrite the dummy value.
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
                        raise ValueError("Could could not extract or parse a valid JSON object from the API response.")
                else:
                    json_string = json_match.group(1)
                    plan_json = json.loads(json_string)

                # 4. Success: Extract tip and return
                progression_tip = self._extract_and_move_progression_tip(plan_json)
                
                # IMPORTANT: Use the enhanced markdown conversion here which performs the calorie calculation
                # This call modifies the `plan_json` in place with the correct `est_calories` value.
                plan_md = self._convert_plan_to_markdown_enhanced(plan_json, user_profile)
                
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
        # The fallback plan's JSON is passed to the markdown converter, where calories are calculated and fixed.
        return {
            "success": False,
            "plan_json": fallback_plan_json,
            "plan_md": self._convert_plan_to_markdown_enhanced(fallback_plan_json, user_profile), 
            "error": error_message,
            "progression_tip": progression_tip 
        }
    
    def _generate_fallback_plan_json(self, user_profile: Dict, day_name: str, day_focus: str, sets: str, reps: str, rest: str) -> Dict:
        """
        [FIX 2 Implementation] Generate simple fallback plan as a JSON object with required structure. 
        Uses the dummy calorie value for consistency with the LLM's required output, 
        as this value will be correctly overwritten by Python's calculation later.
        """
        
        exercise_count = int(self._determine_exercise_count(user_profile.get("session_duration", "30-45 minutes"), user_profile.get("fitness_level", "Beginner (0–6 months)")))
        
        # Consistent steps for compliance
        generic_steps = [
            "Prepare your body and equipment for the movement.",
            "Execute the primary phase of the exercise with control.",
            "Hold or pause briefly at the point of maximum contraction/stretch.",
            "Return slowly to the starting position, maintaining tension and form.",
            "Repeat for the specified repetitions or duration."
        ]
        
        # Fallback dummy calorie value (will be overwritten by Python calculation later in _convert_plan_to_markdown_enhanced)
        DUMMY_CALORIE_VALUE = "Est: 0 Cal (MET: 0.0)"
        
        # Ensure 3-5 steps are formal and complete in the fallback
        base_exercises = [
            {
                "name": "Wall Push-ups (Standard)",
                "benefit": "Targets chest and arms safely (Horizontal Push). Standard exercise.",
                "steps": generic_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Wall",
                "safety_cue": "Keep your body in a straight line from head to heels; avoid sinking your hips.", # FIXED
                "est_calories": DUMMY_CALORIE_VALUE # Use dummy value for consistency, will be overwritten
            },
            {
                "name": "Single-Arm Dumbbell Row",
                "benefit": "Works the back and rear shoulders (Horizontal Pull). Standard exercise.",
                "steps": generic_steps,
                "sets": sets,
                "reps": f"{reps.split('-')[-1]} / side",
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Dumbbell, Bench/Chair",
                "safety_cue": "Maintain a tall, upright posture and pull with your back, not just your arm. Protect your lower back by bracing your core.", # FIXED
                "est_calories": DUMMY_CALORIE_VALUE # Use dummy value for consistency, will be overwritten
            },
            {
                "name": "Chair Squats (Standard)",
                "benefit": "Targets lower body with joint support (Knee Dominant). Standard exercise.",
                "steps": generic_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Chair",
                "safety_cue": "Keep knees tracking directly over your feet; do not let them cave inward. Sit back, not down, keeping chest upright.", # FIXED
                "est_calories": DUMMY_CALORIE_VALUE # Use dummy value for consistency, will be overwritten
            },
            {
                "name": "Plank (Standard Isometric Hold)",
                "benefit": "Strengthens core stability (Anti-Extension). Standard exercise.",
                "steps": generic_steps,
                "sets": sets,
                "reps": "30-45 seconds (or max hold)",
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Yoga Mat",
                "safety_cue": "Keep the spine neutral, maintain a straight line from head to heels, and do not let the hips drop or raise too high.", # FIXED
                "est_calories": DUMMY_CALORIE_VALUE # Use dummy value for consistency, will be overwritten
            },
             {
                "name": "Standing Overhead Band Tricep Extension",
                "benefit": "Targets triceps for arm strength. Standard exercise.",
                "steps": generic_steps,
                "sets": sets,
                "reps": reps,
                "intensity_rpe": "RPE 4-6",
                "rest": rest,
                "equipment": "Resistance Band",
                "safety_cue": "Keep elbows fixed close to your head; avoid flaring them out. If you feel any sharp pain, stop immediately.", # FIXED
                "est_calories": DUMMY_CALORIE_VALUE # Use dummy value for consistency, will be overwritten
            }
        ]
        
        main_exercises = []
        for i in range(exercise_count):
            main_exercises.append(base_exercises[i % len(base_exercises)])
            
        current_level_hold = STATIC_HOLD_SCALING.get(user_profile.get("fitness_level", "Beginner (0–6 months)"), "15-30 seconds")
        
        warmup = [
            # Fallback exercise is Low-Impact High Knees
            {"name": "Low-Impact High Knees (Cardio Warmup)", "benefit": "Elevates heart rate and activates core/legs without jumping (1-2 min duration).", "steps": generic_steps, "sets": "1", "reps": "60-120 (Reps to equate to 1-2 min)", "intensity_rpe": "RPE 1-2", "rest": "15 seconds", "equipment": "Bodyweight", "safety_cue": "Focus on lifting the knees gently; ensure feet land softly and maintain a steady rhythm. Avoid leaning back.", # FIXED
             "est_calories": DUMMY_CALORIE_VALUE}, 
            {"name": "Arm Circles (Upper Body Dynamic Stretch)", "benefit": "Increases shoulder joint range of motion and blood flow.", "steps": generic_steps, "sets": "1", "reps": "15 forward, 15 backward", "intensity_rpe": "RPE 1-2", "rest": "15 seconds", "equipment": "Bodyweight, Chair (if needed)", "safety_cue": "Keep core engaged and maintain small, controlled circles initially. Only move arms in a pain-free range.", # FIXED
             "est_calories": DUMMY_CALORIE_VALUE}, 
            {"name": "Standing Hip Swings (Lower Body Dynamic Stretch)", "benefit": "Improves dynamic flexibility in the hips and hamstrings.", "steps": generic_steps, "sets": "1", "reps": "10 / side", "intensity_rpe": "RPE 1-2", "rest": "15 seconds", "equipment": "Bodyweight, Wall (for support)", "safety_cue": "Use a wall for balance; control the swing and do not force the range of motion. Keep the standing knee slightly soft.", # FIXED
             "est_calories": DUMMY_CALORIE_VALUE}
        ]
        
        cooldown = [
            {"name": "Seated Glute Stretch (Figure-4)", "benefit": "Deep stretch for the gluteal muscles and lower back relief.", "steps": generic_steps, "sets": "1", "hold": f"{current_level_hold} per leg", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Chair", "safety_cue": "Keep the spine straight; lean forward from the hips until a gentle stretch is felt. Never bounce or over-stretch.", # FIXED
             "est_calories": DUMMY_CALORIE_VALUE}, 
            {"name": "Wall Chest Stretch", "benefit": "Opens the chest and improves shoulder posture.", "steps": generic_steps, "sets": "1", "hold": f"{current_level_hold} per arm", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Wall", "safety_cue": "Gently rotate away from the wall; avoid straining the shoulder capsule. Keep the shoulder below the point of pain.", # FIXED
             "est_calories": DUMMY_CALORIE_VALUE}, 
            {"name": "Deep Diaphragmatic Breathing", "benefit": "Calms the nervous system and aids muscle recovery.", "steps": generic_steps, "sets": "1", "hold": "2 minutes (slow, controlled breaths)", "intensity_rpe": "RPE 1-3", "rest": "15 seconds", "equipment": "Bodyweight", "safety_cue": "Breathe into your belly, not your chest. Keep shoulders relaxed and fully focus on the breath.", # FIXED
             "est_calories": DUMMY_CALORIE_VALUE} 
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
    /* Style for the interactive logging buttons */
    .stButton button[kind="secondary"] {
        background-color: #4a4a4a;
        color: white;
        padding: 0.25rem 0.5rem;
        font-size: 0.8rem;
        border-radius: 5px;
    }
    /* Custom Styling for the planned metrics row */
    .planned-metrics p {
        margin: 0.2rem 0;
        font-size: 0.9em;
    }
    .planned-metrics strong {
        color: #764ba2; /* Use a primary color for labels */
        font-weight: 700;
    }
    .planned-metrics {
        border-left: 3px solid #667eea;
        padding-left: 10px;
        margin-bottom: 15px;
        background-color: rgba(255, 255, 255, 0.05); /* Slight background for grouping */
        border-radius: 5px;
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
    # NEW: State for logging actual performance
    if 'logged_performance' not in st.session_state:
        # Structure: {day_name: {exercise_id: {actual_sets: X, actual_reps: Y}}}
        st.session_state.logged_performance = {}
        
    # Initialize the specific_avoidance key in the user_profile structure itself
    if 'specific_avoidance' not in st.session_state.user_profile:
        st.session_state.user_profile['specific_avoidance'] = "None"


# ============ INTERACTIVE UI HELPER FUNCTIONS ============

def calculate_performance_calorie_burn(exercise_index: str, day_name: str, advisor: FitnessAdvisor, weight_kg: float) -> float:
    """
    Calculates the real-time calorie burn based on logged sets and 
    the actual MET rate, as requested by the user, using the formula
    Calories = (MET * Weight_KG * 3.5) / 200 * (Duration in minutes).
    """
    
    logged_data = st.session_state.logged_performance.get(day_name, {}).get(exercise_index, {})
    actual_sets = logged_data.get('actual_sets', 0)
    # Note: actual_reps is either reps for strength or seconds for time-based/cardio
    actual_units_per_set = logged_data.get('actual_reps', 0) 
    
    # 1. Basic checks
    if actual_sets <= 0 or actual_units_per_set <= 0 or weight_kg <= 0:
        return 0.0

    plan = st.session_state.all_json_plans.get(day_name)
    profile = st.session_state.user_profile
    if not plan or not profile:
        return 0.0

    # 2. Find the exercise data and section type
    ex_data = None
    section_map = {'warmup': plan.get('warmup', []), 'main': plan.get('main_workout', []), 'cooldown': plan.get('cooldown', [])}
    section_key = None
    
    try:
        section_key, idx = exercise_index.split('_')
        idx = int(idx) - 1
        
        if section_key in section_map and 0 <= idx < len(section_map[section_key]):
            ex_data = section_map[section_key][idx]
    except:
        return 0.0

    if not ex_data:
        return 0.0
        
    exercise_name = ex_data.get('name', 'Unknown Exercise')
    fitness_level = profile.get('fitness_level', "Beginner (0–6 months)")

    # 3. Determine MET value based on the exercise and user level
    # Use the stored MET value if available, otherwise look it up again (robustness)
    met_value = ex_data.get('met_value') 
    if not met_value:
         met_value = advisor._get_met_value(exercise_name, fitness_level) 
    
    if met_value <= 0:
        # Fallback to a safe general MET if lookup fails
        met_value = 3.0
        
    # 4. Determine total duration in minutes based on ACTUAL performance
    
    total_seconds = 0.0
    
    # Check if the exercise is time-based (hold/cooldown/cardio warmup)
    name_lower = exercise_name.lower()
    
    is_time_based_exercise = False
    if section_key == 'cooldown':
        is_time_based_exercise = True
    # Check main/warmup for explicit time-based descriptions
    elif ('hold' in name_lower or 'second' in name_lower or 'minute' in name_lower):
        is_time_based_exercise = True
    # Special check for warmup cardio (which is logged in seconds)
    elif section_key == 'warmup' and ('march' in name_lower or 'jog' in name_lower or 'jack' in name_lower or 'cardio' in name_lower):
         is_time_based_exercise = True

    if is_time_based_exercise:
        # If it's time-based, actual_units_per_set is the duration in seconds per set
        total_seconds = actual_sets * actual_units_per_set
    else:
        # If it's rep-based, estimate time per rep (5 seconds is a conservative estimate for strength/dynamic)
        # 5 seconds per rep (assuming 3-1-1 tempo)
        estimated_seconds_per_set = (actual_units_per_set * 5)
        total_seconds = actual_sets * estimated_seconds_per_set
        
    total_minutes = total_seconds / 60.0

    # 5. Apply the Calorimetry Formula
    # Formula: Calories = (MET * Weight_KG * 3.5) / 200 * Minutes
    
    if total_minutes == 0:
        return 0.0

    estimated_calories = (met_value * weight_kg * 3.5) / 200 * total_minutes
    
    return max(0.0, estimated_calories)

def display_interactive_workout_day(day_name: str, plan_json: Dict, profile: Dict, advisor: FitnessAdvisor):
    """Dynamically renders the workout plan with interactive logging."""
    
    weight_kg = profile.get('weight_kg', 70.0)
    
    # Initialize logged performance for the day if missing
    if day_name not in st.session_state.logged_performance:
        st.session_state.logged_performance[day_name] = {}

    def update_sets(day, ex_id, delta):
        st.session_state.logged_performance[day][ex_id]['actual_sets'] = max(0, st.session_state.logged_performance[day][ex_id]['actual_sets'] + delta)

    def render_section(section_data: List[Dict], section_title: str, section_key: str):
        st.markdown(f"## 🤸 {section_title} ")
        
        for idx, exercise in enumerate(section_data):
            # Unique identifier for the exercise in session state
            # e.g., 'main_1', 'warmup_2'
            ex_id = f"{section_key}_{idx + 1}"
            
            # Initialize logged data for this specific exercise
            if ex_id not in st.session_state.logged_performance[day_name]:
                # Default to 0 actual sets/reps
                st.session_state.logged_performance[day_name][ex_id] = {'actual_sets': 0, 'actual_reps': 0}
            
            # Planned values for display
            planned_sets = exercise.get('sets', '1')
            
            # Determine planned unit
            if section_key == 'cooldown':
                planned_unit_str = exercise.get('hold', '30 seconds')
                planned_unit_label = "Hold (sec)"
            elif 'main' in section_key and ('second' in exercise.get('reps', '').lower() or 'minute' in exercise.get('reps', '').lower() or 'max hold' in exercise.get('reps', '').lower()):
                planned_unit_str = exercise.get('reps', '30 seconds')
                planned_unit_label = "Hold (sec)"
            else:
                planned_unit_str = exercise.get('reps', '10-15')
                planned_unit_label = "Reps"

            # Parse a single numeric value from the planned string for the logging widget default
            try:
                if '-' in planned_unit_str:
                    low = int(re.search(r'(\d+)', planned_unit_str.split('-')[0]).group(1))
                    high_part = planned_unit_str.split('-')[-1]
                    high = int(re.search(r'(\d+)', high_part).group(1))
                    planned_numeric_default = int((low + high) / 2)
                elif re.search(r'(\d+)', planned_unit_str):
                    planned_numeric_default = int(re.search(r'(\d+)', planned_unit_str).group(1))
                else:
                    planned_numeric_default = 10 # Default to 10
            except:
                planned_numeric_default = 10


            # --- UI RENDERING ---
            st.markdown(f"#### **{idx + 1}. {exercise.get('name', 'N/A')}**")
            
            # 1. Planned Metrics (Consolidated and styled)
            planned_col1, planned_col2, planned_col3, planned_col4, planned_col5 = st.columns([1, 1, 1, 1, 4])
            
            planned_col1.markdown(f"<div class='planned-metrics'><p><strong>Sets:</strong> {planned_sets}</p></div>", unsafe_allow_html=True)
            planned_col2.markdown(f"<div class='planned-metrics'><p><strong>{planned_unit_label}:</strong> {planned_unit_str}</p></div>", unsafe_allow_html=True)
            planned_col3.markdown(f"<div class='planned-metrics'><p><strong>Rest:</strong> {exercise.get('rest', 'N/A')}</p></div>", unsafe_allow_html=True)
            planned_col4.markdown(f"<div class='planned-metrics'><p><strong>RPE:</strong> {exercise.get('intensity_rpe', 'N/A').replace('RPE ', '')}</p></div>", unsafe_allow_html=True)
            planned_col5.markdown(f"<div class='planned-metrics'><p><strong>Equipment:</strong> {exercise.get('equipment', 'N/A')}</p></div>", unsafe_allow_html=True)
            
            st.markdown(f"*{exercise.get('benefit', 'N/A')}*")
            # FIX: Display Safety Cue here.
            st.markdown(f"> **Safety Cue:** *{exercise.get('safety_cue', 'N/A')}*")

            # 2. Logging Row for Actual Performance
            # Adjusted columns for better alignment: Sets Buttons | Sets Count | Rep/Unit Label | Rep/Unit Input | Calorie Burn
            col_log_sets_btn, col_log_sets_count, col_log_units_label, col_log_units_input, col_log_cal = st.columns([0.8, 0.6, 1.2, 1.2, 3.5])
            
            # --- Actual Sets Logging ---
            sets_key = f"sets_log_{ex_id}_{day_name}"
            current_sets = st.session_state.logged_performance[day_name][ex_id]['actual_sets']
            
            col_log_sets_btn.markdown(f"**Sets Achieved**") # Label for buttons
            
            # Row 2: Set Buttons
            col_set_minus, col_set_plus = col_log_sets_btn.columns(2)
            col_set_minus.button("–", key=f"set_minus_{sets_key}", help="Decrease sets",
                             on_click=lambda day=day_name, id_=ex_id: update_sets(day, id_, -1),
                             use_container_width=True)
            col_set_plus.button("+", key=f"set_plus_{sets_key}", help="Increase sets",
                             on_click=lambda day=day_name, id_=ex_id: update_sets(day, id_, 1),
                             use_container_width=True)

            col_log_sets_count.markdown(f"<h3 style='margin-top: 20px;'>{current_sets}</h3>", unsafe_allow_html=True)


            # --- Actual Reps/Duration Logging (Units) ---
            units_key = f"units_log_{ex_id}_{day_name}"
            current_units = st.session_state.logged_performance[day_name][ex_id]['actual_reps']
            
            # Units display and input
            # Use the dedicated calorie rate function to get the correct unit (Rep or Sec)
            rate_per_unit, rate_unit = advisor._calculate_calorie_rate(exercise.get('name', ''), weight_kg)
            
            # If the exercise is the FIRST cardio warmup, enforce SECONDS for logging and default to 90
            if idx == 0 and section_key == 'warmup':
                 unit_input_default = 90
                 unit_input_step = 5
                 rate_unit = "Sec" # ENFORCE SECONDS for warm-up cardio logging
            else:
                 unit_input_default = planned_numeric_default
                 unit_input_step = 1

            col_log_units_label.markdown(f"**{rate_unit} per Set**", help=f"Actual reps or seconds completed in each of the {current_sets} sets.")

            max_units = 300 if rate_unit == "Sec" else 150 
            
            new_units = col_log_units_input.number_input(
                f"Actual {rate_unit}", 
                min_value=0, 
                max_value=max_units,
                value=current_units if current_units > 0 else unit_input_default,
                key=units_key,
                step=unit_input_step,
                label_visibility="collapsed" # Hide the label to keep it compact
            )
            
            # Update the session state when the number input changes
            if new_units != current_units:
                # IMPORTANT: We must update the session state here to reflect the change
                st.session_state.logged_performance[day_name][ex_id]['actual_reps'] = new_units
                # Since Streamlit reruns on interaction, the calorie calculation will pick up the new value automatically.

            # --- Calorie Burn Display (UPDATED RATE CALCULATION) ---
            total_cal = calculate_performance_calorie_burn(ex_id, day_name, advisor, weight_kg)
            
            # Determine the MET value and calculate the rate per unit based on the type of unit (Rep or Sec)
            met_value = exercise.get('met_value', advisor._get_met_value(exercise.get('name', ''), profile.get('fitness_level', "Beginner (0–6 months)")))
            
            # Formula: Cal/Minute = (MET * Weight_KG * 3.5) / 200
            cal_per_minute = (met_value * weight_kg * 3.5) / 200
            cal_per_unit_rate = 0.0
            if rate_unit == "Sec":
                # If the unit is seconds, the rate is Cal/minute / 60
                cal_per_unit_rate = cal_per_minute / 60
            elif rate_unit == "Rep":
                # If the unit is reps, the rate is Cal/minute * (estimated seconds per rep / 60 seconds)
                # We estimate 5 seconds per rep for strength/dynamic movements
                cal_per_unit_rate = (cal_per_minute * 5) / 60 

            col_log_cal.markdown(f"**🔥 Performance Burn**")
            col_log_cal.info(f"**{round(total_cal)} Cal** (Rate Est: {cal_per_unit_rate:.2f} Cal/{rate_unit})")
            
            # Display Steps (Always display steps below the logging)
            with st.expander("Show Detailed Steps"):
                st.markdown("##### How to Perform:")
                steps = exercise.get('steps', [])
                if steps:
                    for step_idx, step in enumerate(steps):
                        st.markdown(f"{step_idx + 1}. {step.strip()}")
                else:
                    st.markdown("Steps missing from plan - Follow general form.")
            
            st.divider() # New separator for visual cleanliness
            
    # Render all sections
    if plan_json:
        # Warmup
        render_section(plan_json.get('warmup', []), "Warm-Up", 'warmup')
        # Main Workout
        render_section(plan_json.get('main_workout', []), f"Main Workout ({plan_json.get('main_workout_category', 'N/A')})", 'main')
        # Cool-Down
        render_section(plan_json.get('cooldown', []), "Cool-Down", 'cooldown')

        # Total Summary
        st.markdown("## 🔥 **Daily Summary**")
        
        # Calculate total for the day
        total_daily_calories = 0
        for ex_id in st.session_state.logged_performance.get(day_name, {}):
            total_daily_calories += calculate_performance_calorie_burn(ex_id, day_name, advisor, weight_kg)

        st.info(f"**TOTAL Calories Burned (Based on Logged Performance):** **{round(total_daily_calories)} Cal**")
        
        # Display safety notes
        st.markdown("### 📝 Safety and General Notes")
        safe_notes = [note for note in plan_json.get('safety_notes', []) if not note.strip().lower().startswith("progression tip:")]
        if safe_notes:
            for idx, note in enumerate(safe_notes):
                st.markdown(f"**{idx + 1}.** {note}\n")
        else:
            st.markdown("No specific safety notes provided for this session.")
        
    else:
        st.error("Workout plan JSON is missing or invalid for this day.")


# ============ MAIN APPLICATION ============
def main():
    """Main application"""
    
    # FIX 1: Ensure session state is initialized before widgets access it
    initialize_session_state() 
    
    inject_custom_css()
    advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)
    
    # Header
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">💪 FriskaAI Fitness Coach </h1>
        <p class="header-subtitle">AI-Powered Personalized Fitness Plans</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- MAIN FORM (for batch submission) ---
    with st.form("fitness_form"):
        
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
        
        # Primary Goal Selection
        primary_goal_options = PRIMARY_GOALS
        primary_goal_default_index = primary_goal_options.index(profile.get('primary_goal', 'Weight Maintenance'))
        primary_goal = st.selectbox(
            "Primary Goal *",
            primary_goal_options, key="primary_goal_input", index=primary_goal_default_index
        )
        
        # Secondary Goal Selection
        secondary_goal_options = ["None"] + SECONDARY_GOALS
        secondary_goal_default_value = profile.get('secondary_goal', 'None')
        secondary_goal_default_index = secondary_goal_options.index(secondary_goal_default_value if secondary_goal_default_value in secondary_goal_options else 'None')
        secondary_goal = st.selectbox(
            "Secondary Goal (Optional)",
            secondary_goal_options, key="secondary_goal_input", index=secondary_goal_default_index
        )
        
        # New Body Part Selection
        st.subheader("🏋️ Target Focus")
        body_part_options = ["Upper Body", "Lower Body", "Core", "Full Body"]
        body_parts_default = profile.get('target_body_parts', ["Full Body"])
        target_body_parts = st.multiselect(
            "Select Body Parts to Focus On:",
            body_part_options, 
            default=body_parts_default, 
            key="body_parts_input"
        )
        if not target_body_parts:
            target_body_parts = ["Full Body"]

        # Fitness Level (Experience)
        st.subheader("⏱️ Experience Level")
        fitness_level_options = list(TRAINING_LEVELS.keys())
        fitness_level_default_index = fitness_level_options.index(profile.get('fitness_level', 'Beginner (0–6 months)'))
        fitness_level = st.selectbox(
            "Training Experience (Level) *",
            fitness_level_options, key="fitness_level_input", index=fitness_level_default_index
        )
        
        level_info = TRAINING_LEVELS[fitness_level]
        st.info(f"**{fitness_level}** (RPE {level_info['rpe_range']}): {level_info['description']}")
        
        # Medical Conditions
        st.subheader("🏥 Health Screening")
        
        # Determine initial default selection: use saved profile or [] (empty) on first run
        initial_multiselect_default = profile.get('medical_conditions', [])
        
        medical_conditions = st.multiselect(
            "Medical Conditions *",
            MEDICAL_CONDITIONS_OPTIONS, 
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
        
        # --- Streamlined Specific Exercise Avoidance (Inside Form) ---
        
        st.warning("⚠️ **Specific Exercise Restrictions**")
        
        # Get the default text from profile (if it exists)
        initial_avoid_text = profile.get('specific_avoidance', '') 
        if initial_avoid_text == 'None':
            initial_avoid_text = ''
        
        # Use a single text area with an instructional prompt
        specific_avoidance_input = st.text_area(
            "Have you been advised to avoid any specific exercises? (If yes, please list them below):",
            placeholder="E.g., 'Heavy deadlifts, overhead pressing due to shoulder issue, any exercise that causes sharp pain in the elbow.'",
            height=100,
            key="specific_avoidance_text_input", 
            value=initial_avoid_text
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
        
        # --- FIX: Auto-set equipment if Gym is selected ---
        if workout_location == "Gym":
            st.info("✅ **Gym Selected:** We will assume access to standard gym equipment (Machines, Cables, Barbells, Dumbbells, Bench).")
            # Force full equipment list so the AI knows it has options
            equipment = ["Full Gym Access", "Machines", "Cables", "Barbells", "Dumbbells", "Bench", "Pull-up Bar", "Kettlebells"]
        else:
            # Show manual selector for Home/Outdoor
            eq_options = ["Bodyweight Only", "Dumbbells", "Resistance Bands", "Kettlebells", "Barbell", "Bench", "Pull-up Bar", "Yoga Mat"]
            equipment = st.multiselect(
                "Select all available equipment:", 
                eq_options, 
                default=profile.get('available_equipment', ["Bodyweight Only"]), 
                key="equipment_input"
            )
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
                    
                # Store final avoidance: If the text area has content, use it. Otherwise, store "None".
                final_avoidance = specific_avoidance_input.strip() if specific_avoidance_input.strip() else "None"

                st.session_state.user_profile = {
                    "name": name.strip(),
                    "age": age,
                    "gender": gender,
                    "weight_kg": weight_kg,
                    "height_cm": height_cm,
                    "bmi": round(final_bmi, 1) if final_bmi > 0 else 0,
                    "primary_goal": primary_goal,
                    "secondary_goal": secondary_goal,
                    "target_body_parts": target_body_parts, # NEW: Store selected body parts
                    "fitness_level": fitness_level,
                    "medical_conditions": medical_conditions,
                    "physical_limitation": physical_limitation.strip(),
                    "specific_avoidance": final_avoidance, 
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
                # Reset logged performance on new generation
                st.session_state.logged_performance = {} 
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
            st.success("✅ Your fitness plan is ready! Time to log your performance.")
        else:
            st.error("⚠️ Plan generation complete, but one or more days failed (used fallback). Check the API key and console logs for details.")
        
        st.session_state.fitness_plan_generated = True
        st.session_state.generation_in_progress = False
        st.rerun() 
    
    # =================================================================================
    # DISPLAY PLANS (INTERACTIVE LOGGING)
    # =================================================================================
    else:
        profile = st.session_state.user_profile
        
        # FIX: Ensure best_tip has a safe default value if no plans have been generated yet.
        days = profile.get('days_per_week', [])
        best_tip = "Complete the form and generate your plan to see your focus for next week."
        if days:
            best_tip = st.session_state.all_progression_tips.get(days[-1], "Focus on maintaining consistent activity and improving form.") 
        
        if st.session_state.fitness_plan_generated:
            st.markdown(f"👋 Welcome, **{profile.get('name', 'User')}**!")
            st.markdown(f"Your Personalized Fitness Plan is Ready")
            st.markdown(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 🎯 Goal: **{profile.get('primary_goal', 'N/A')}** | 💪 Level: **{profile.get('fitness_level', 'N/A')}**")
            
            st.markdown("\n")
            
            if profile.get('physical_limitation'):
                st.warning(f"⚠️ **Accommodated Limitations:** {profile['physical_limitation']}")
            
            # FIX: Use .get() with a default value to prevent KeyError on initial load
            specific_avoidance_text = profile.get('specific_avoidance', 'None')
            if specific_avoidance_text != 'None':
                 st.warning(f"⚠️ **Specific Avoidance:** Exercises avoided involving: {specific_avoidance_text}")
            
            st.markdown("---")


            # Display plans
            st.markdown("## 📅 Your Weekly Workout Schedule ")
            st.markdown("Log your actual sets and reps/seconds performed to get a real-time calorie burn calculation.")
            
            for idx, day in enumerate(profile.get('days_per_week', [])):
                if day in st.session_state.all_json_plans and st.session_state.all_json_plans[day]:
                    plan_json = st.session_state.all_json_plans[day]
                    
                    # [UPDATE 1] Day-wise Workout Title Fix: Use the day and the category for a descriptive title
                    day_title = f"{day} - {plan_json.get('main_workout_category', 'Workout')}" 
                    
                    with st.expander(f"📋 {day_title} Workout Log", expanded=True if idx == 0 else False):
                        
                        st.markdown(f"### **{day_title}**") # Display the dynamic day title
                        
                        # NEW INTERACTIVE DISPLAY
                        display_interactive_workout_day(day, plan_json, profile, advisor) 
                        
                        # If it was a fallback plan, show the error message
                        if not st.session_state.workout_plans.get(day, {}).get('success'):
                            st.warning(f"⚠️ **API Error:** Showing fallback plan. Error: {st.session_state.workout_plans.get(day, {}).get('error', 'Unknown error')}.")

                elif day in st.session_state.workout_plans:
                    # Fallback to display the static markdown if JSON failed, but markdown was generated
                    plan_data = st.session_state.workout_plans[day]
                    st.error("Could not load interactive view (JSON parsing issue). Showing static plan.")
                    st.markdown(plan_data['plan_md'])
                else:
                    st.warning("Plan not available")
            
            
            
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
                    st.session_state.logged_performance = {}
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
                    "plans_json": st.session_state.all_json_plans,
                    "logged_performance": st.session_state.logged_performance # Include logged data for completeness
                }
                json_content = json.dumps(json_export_data, indent=4)
                st.download_button(
                    label="⬇️ Download Plan (JSON)",
                    data=json_content,
                    file_name=f"FriskaAI_Plan_{profile.get('name', 'User')}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )

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
**Specific Avoidance Advice:** {profile.get('specific_avoidance', 'None')}

---

## 📈 Weekly Progression Goal
**Your Focus for Next Week:** {progression_tip}

---

"""
    
    # Add each workout day
    for day in profile.get('days_per_week', []):
        if day in workout_plans and workout_plans[day].get('plan_md'):
            status = "✅ SUCCESS" if workout_plans[day]['success'] else "⚠️ FALLBACK PLAN (API Error)"
            
            # [UPDATE 1] Dynamic Day Title Fix: Use the day and the category for a descriptive title
            plan_json = st.session_state.all_json_plans.get(day, {})
            main_category = plan_json.get('main_workout_category', 'Workout')
            
            md_content += f"\n## {day} Workout - {main_category} ({status})\n\n"
            md_content += f"{workout_plans[day]['plan_md']}\n\n---\n"
    
    # Add footer
    md_content += """

## ⚠️ Important Disclaimers

1. This workout plan is AI-generated guidance and NOT a substitute for professional medical advice
2. Consult your physician before starting any exercise program
3. Stop exercising immediately if you experience pain, dizziness, or unusual symptoms

---

**Generated by FriskaAI Fitness Coach**
"""
    
    return md_content

# ============ RUN APPLICATION ============
if __name__ == "__main__": 
    main()
