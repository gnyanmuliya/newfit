import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import re
import random
import requests # Library for making HTTP requests (for Gemini API)
import json # Library for handling JSON data
import time # For exponential backoff

# Note: The API Key for the Gemini API is automatically provided by the Canvas environment 
# when the apiKey variable is left as an empty string and used in the URL.
API_KEY = "" 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

# ============ CONFIGURATION & DATA DEFINITIONS ============

FITNESS_LEVELS = {
    'Level 1 – Assisted / Low Function': {'description': 'Requires significant support; focuses on basic movement and stability.', 'rpe_range': '2-3', 'max_complexity': 1},
    'Level 2 – Beginner Functional': {'description': 'Basic movement patterns, low impact, focus on form and core control.', 'rpe_range': '3-4', 'max_complexity': 2},
    'Level 3 – Moderate / Independent': {'description': 'Can perform unassisted movements with mild fatigue. Regular activity 2-3x/week.', 'rpe_range': '4-6', 'max_complexity': 3},
    'Level 4 – Active Wellness': {'description': 'Regular training experience, higher intensity, pushing strength and endurance limits.', 'rpe_range': '6-8', 'max_complexity': 4},
    'Level 5 – Adaptive Advanced': {'description': 'Highly experienced, requires advanced variations and maximal intensity/endurance work.', 'rpe_range': '7-9', 'max_complexity': 5},
}

GOAL_OPTIONS = [
    "Weight Loss", "Muscle Gain (Hypertrophy)", "Strength Gain", "Cardiovascular Fitness",
    "Flexibility & Mobility", "Rehabilitation & Injury Prevention", "Posture & Balance Improvement",
    "General Fitness", "Other (Custom Goal)"
]

MEDICAL_CONDITIONS = ["None", "Hypertension", "Obesity / Overweight", "Type 2 Diabetes", "Chronic Low Back Pain", "Osteoporosis", "Other"]

LOCATION_OPTIONS = ["Home", "Gym", "Outdoor"]

EQUIPMENT_OPTIONS = ["Bodyweight Only", "Dumbbells", "Resistance Bands", "Kettlebells",
                     "Barbell", "Bench", "Pull-up Bar", "Yoga Mat", "Machines", "Stable Chair", "TRX", "Cables"]

# ACSM time breakdown logic (minutes/exercise count) based on duration
DURATION_MAP = {
    # Main exercises are allocated based on the 4 resistance categories for BALANCE
    "15-20 minutes": {'total_time': 18, 'warmup_count': 3, 'cooldown_count': 2, 'main_count': 5}, 
    "20-30 minutes": {'total_time': 25, 'warmup_count': 3, 'cooldown_count': 2, 'main_count': 7}, 
    "30-45 minutes": {'total_time': 38, 'warmup_count': 3, 'cooldown_count': 2, 'main_count': 9}, 
    "45-60 minutes": {'total_time': 53, 'warmup_count': 3, 'cooldown_count': 2, 'main_count': 11},
}

EXERCISE_DATA_FILE = "Latest exercise database- New model.csv"

# Define Resistance Categories
RESISTANCE_CATS = ['Upper Body Push', 'Upper Body Pull', 'Lower Body', 'Core']

@st.cache_data
def load_exercise_data():
    """
    Loads the actual exercise database from CSV, cleans it, and creates required filtering columns.
    """
    try:
        # NOTE: If this file is not present in the same directory, this will fail.
        df = pd.read_csv(EXERCISE_DATA_FILE, encoding='utf-8')
    except FileNotFoundError:
        st.error(f"❌ Error: Exercise database file '{EXERCISE_DATA_FILE}' not found. Please ensure the file is uploaded and in the correct directory.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading exercise data: {e}")
        return pd.DataFrame()

    # --- Data Cleaning and Augmentation ---
    
    def extract_level_number(level_str):
        match = re.search(r'Level (\d+)', str(level_str))
        return int(match.group(1)) if match else 0
        
    df['Complexity_Level'] = df['Fitness Level'].apply(extract_level_number)
    
    required_cols = ['Goals', 'Available Equipment', 'Category', 'Exercise Name', 'Target Region', 'Contraindications']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Internal Error: Missing required columns in CSV: {list(set(required_cols) - set(df.columns))}")
        return pd.DataFrame()

    # Robustly create Goals_List and Equipment_List for reliable filtering
    df['Goals_List'] = df['Goals'].fillna('').astype(str).apply(
        lambda x: [s.strip().lower() for s in x.split(',')]
    )
    df['Equipment_List'] = df['Available Equipment'].fillna('').astype(str).apply(
        lambda x: [s.strip().lower() for s in x.replace("/", ",").split(',')]
    )
    
    # Create Concept_Group (e.g., 'reverse lunge' -> 'reverse')
    df['Concept_Group'] = df['Exercise Name'].str.split(' ').str[0].str.lower()
    
    # 4. Create Resistance Category (Crucial for balancing Push/Pull/Lower/Core)
    def determine_resistance_category(row):
        category = row['Category']
        name = row['Exercise Name'].lower()
        target = row['Target Region'].lower()
        
        if 'Body' in category or 'Strength' in category or 'Resistance' in category:
            if 'push' in name or 'press' in name or 'tricep' in name or 'chest' in target or 'shoulder' in target:
                return 'Upper Body Push'
            elif 'row' in name or 'pull' in name or 'bicep' in name or 'back' in target:
                return 'Upper Body Pull'
            elif 'core' in category.lower() or 'plank' in name or 'twist' in name or 'abs' in target or 'oblique' in target:
                 return 'Core'
            elif 'lower' in category.lower() or 'squat' in name or 'lunge' in name or 'deadlift' in name or 'hip' in name or 'glute' in target:
                 return 'Lower Body'
            
        return category # Fallback for Warm-up/Cool-down/Mobility
        
    df['Resistance_Category'] = df.apply(determine_resistance_category, axis=1)
    
    # Ensure Category is clean for grouping
    df['Category'] = df['Category'].astype(str).str.strip()
    
    return df

# Global sets for A/B split variety tracking
used_concept_groups_A = set()
used_concept_groups_B = set()

def calculate_bmi(weight_kg: float, height_cm: float) -> Optional[float]:
    """Calculates BMI from weight (kg) and height (cm)."""
    if weight_kg > 0 and height_cm > 0:
        return weight_kg / ((height_cm / 100) ** 2)
    return None

def get_session_counts(session_duration: str) -> Dict[str, int]:
    """Retrieves the target number of exercises for the session."""
    return DURATION_MAP.get(session_duration, DURATION_MAP["45-60 minutes"]) 

def get_training_split(days_count: int, fitness_level: str) -> List[str]:
    """
    Determines the workout distribution rule (A-B-A split for variety).
    """
    match = re.search(r'\d+', fitness_level)
    level_num = int(match.group(0)) if match else 3
    
    if days_count == 1:
        return ["Full-Body A"]
    elif days_count == 2:
        return ["Full-Body A", "Full-Body B"] if level_num >= 4 else ["Full-Body A", "Full-Body A"]
    elif days_count == 3:
        # Levels 3-5: Use A-B-A pattern for variety
        return ["Full-Body A", "Full-Body B", "Full-Body A"] if level_num >= 3 else ["Full-Body A"] * 3
    elif days_count == 4:
        return ["Split A", "Split B", "Split A", "Split B"]
    elif days_count == 5:
        return ["Split A", "Split B", "Split A", "Split B", "Split A"]
    elif days_count == 6:
        return ["Split A", "Split B", "Split A", "Split B", "Split A", "Split B"]
    elif days_count == 7:
        return ["Split A", "Split B", "Active Recovery", "Split A", "Split B", "Split A", "Split B"]
    return ["Full-Body A"] * days_count 

def filter_and_select_exercises(df: pd.DataFrame, profile: Dict[str, Any]) -> pd.DataFrame:
    """
    Filters the exercise dataframe based on ALL user profile and goal/level logic.
    """
    
    filtered_df = df.copy()
    session_counts = get_session_counts(profile['session_duration'])
    target_main_count = session_counts['main_count']
    
    # 1. Safety Filter (Medical Conditions & Physical Limitations)
    medical_conditions = [c.lower() for c in profile.get('medical_conditions', []) if c != "None"]
    physical_limitations = profile.get('physical_limitations', '').lower()
    
    if (medical_conditions or physical_limitations) and 'Contraindications' in filtered_df.columns:
        exclusion_keywords = medical_conditions
        exclusion_keywords.extend([word.strip() for word in re.split(r'[^\w\s]', physical_limitations) if len(word) > 2])
        if exclusion_keywords:
            exclusion_pattern = '|'.join(re.escape(k) for k in exclusion_keywords)
            filtered_df = filtered_df[
                ~filtered_df['Contraindications'].fillna('').str.lower().str.contains(exclusion_pattern, na=False)
            ]
            st.info(f"Filtered out exercises contraindicated by: **{', '.join(exclusion_keywords[:3])}...**")
    
    # 2. Level & Complexity Filter 
    user_level_str = profile['fitness_level']
    user_max_complexity = FITNESS_LEVELS[user_level_str]['max_complexity']
    filtered_df = filtered_df[filtered_df['Complexity_Level'] <= user_max_complexity]
    
    # 2b. Exclude overly assisted movements for Level 3 and above
    if user_max_complexity >= 3:
        assisted_keywords = r'assisted|seated|wall' 
        is_strength_category = filtered_df['Category'].str.contains('Body|Strength|Resistance', case=False, na=False)
        is_assisted = filtered_df['Exercise Name'].str.lower().str.contains(assisted_keywords, na=False)
        filtered_df = filtered_df[~(is_strength_category & is_assisted)].copy()
        
    # 3. Equipment Filter (Rule 6)
    available_equipment = [e.lower().replace(" ", "") for e in profile.get('available_equipment', ["Bodyweight Only"])]
    
    def has_required_equipment(exercise_eq_list):
        if 'bodyweightonly' in available_equipment and any('bodyweight' in eq for eq in exercise_eq_list):
            return True
        for required_eq in exercise_eq_list:
            if required_eq.replace(" ", "") in available_equipment:
                return True
        return False
    
    filtered_df = filtered_df[filtered_df['Equipment_List'].apply(has_required_equipment)]

    # 4. Location Filter (Rule 5)
    location = profile.get('workout_location')
    if location == "Home":
        gym_only_forbidden = ['machines', 'barbells', 'cables', 'pull-upbar', 'barbell', 'cable'] 
        def is_home_compatible(exercise_eq_list):
            return not any(eq.replace(" ", "") in gym_only_forbidden for eq in exercise_eq_list)
        filtered_df = filtered_df[filtered_df['Equipment_List'].apply(is_home_compatible)]
    elif location == "Gym":
        filtered_df = filtered_df[~filtered_df['Available Equipment'].fillna('').str.lower().str.contains('outdoor only', na=False)]
    elif location == "Outdoor":
        outdoor_allowed_eq = ['bodyweight', 'outdooronly', 'mat', 'wall', 'bench']
        def is_outdoor_compatible(exercise_eq_list):
            return all(eq.replace(" ", "").replace("/", "").strip() in outdoor_allowed_eq for eq in exercise_eq_list)
        filtered_df = filtered_df[filtered_df['Equipment_List'].apply(is_outdoor_compatible)]
    
    
    # 5. Goal Alignment Filter (Conditional Relaxation for generation volume)
    goal_lower = profile['primary_goal'].lower().split('(')[0].strip()
    
    # Filter 1: Strict Goal Match
    strict_goal_df = filtered_df[filtered_df['Goals_List'].apply(lambda x: any(goal_lower in g for g in x))].copy()
    
    # If strict goal matching is insufficient, relax the goal criteria.
    if len(strict_goal_df) < target_main_count:
        compatible_goals = [goal_lower, 'strength gain', 'general fitness', 'posture & balance improvement', 'cardiovascular fitness']
        relaxed_goal_df = filtered_df[filtered_df['Goals_List'].apply(
            lambda x: any(comp_goal in g for g in x for comp_goal in compatible_goals)
        )].copy()
        
        filtered_df = relaxed_goal_df if len(relaxed_goal_df) >= target_main_count else (strict_goal_df if not strict_goal_df.empty else filtered_df)
    else:
        filtered_df = strict_goal_df

    # 6. CRITICAL HYPERTROPHY FILTERING (Addressing RPE and Equipment conflict)
    if profile['primary_goal'] in ["Muscle Gain (Hypertrophy)", "Strength Gain"]:
        
        # Function to check if the max RPE is at least 5 (Lowering threshold to RPE 5+ to prevent pool exhaustion)
        def meets_stimulus_rpe(rpe_str):
            if pd.isna(rpe_str): return False
            try:
                # FIX: Check for RPE 5+ instead of 7+ to keep more exercises in the running pool.
                numbers = [int(n) for n in re.findall(r'\d+', str(rpe_str))]
                return max(numbers) >= 5
            except:
                return False
        
        # Drop any exercise that cannot achieve RPE 5+ (eliminates dedicated mobility/stretches from the main pool)
        filtered_df = filtered_df[filtered_df['RPE'].apply(meets_stimulus_rpe)].copy()
        
        # Equipment Prioritization (Addressing the Bodyweight penalty leading to empty pool)
        has_loadable_equipment = any(eq in available_equipment for eq in ['dumbbells', 'kettlebells', 'barbell', 'cables'])
        
        # FIX: Only apply the bodyweight penalty if we have a very large pool to start with (3x target)
        # This prevents the filter from wiping out the entire pool when data is sparse.
        if has_loadable_equipment and len(filtered_df) > target_main_count * 3:
            
            # Identify exercises that are bodyweight AND are suitable for resistance
            is_bodyweight_strength = filtered_df['Equipment_List'].apply(
                # If only 'bodyweight' is in the list AND it's a strength category
                lambda x: 'bodyweightonly' in x or ('bodyweight' in x and len(x) == 1)
            )
            is_resistance_category = filtered_df['Resistance_Category'].isin(['Upper Body Push', 'Upper Body Pull', 'Lower Body'])
            
            # Drop pure bodyweight resistance movements to force selection of weighted movements
            temp_df = filtered_df[~(is_bodyweight_strength & is_resistance_category)].copy()

            # Ensure the pool isn't wiped out before assigning it back
            if len(temp_df) >= target_main_count:
                filtered_df = temp_df
            # ELSE: If filtering bodyweight would leave us with too few weighted exercises, keep the bodyweight exercises as a necessary fallback.
        
        
    return filtered_df

# ============ AI FALLBACK IMPLEMENTATION ============

def generate_ai_exercise(profile: Dict[str, Any], res_cat: str) -> Optional[Dict[str, Union[str, float]]]:
    """
    Uses the Gemini API to generate a high-quality exercise fallback when the CSV pool is empty.
    """
    
    available_equipment = ', '.join(profile.get('available_equipment', ["Bodyweight Only"]))
    
    # 1. Define the mandatory JSON schema for the response
    schema = {
        "type": "OBJECT",
        "properties": {
            "Exercise Name": {"type": "STRING", "description": "The name of the exercise."},
            "Target Region": {"type": "STRING", "description": "The primary muscle group targeted."},
            "Sets": {"type": "INTEGER", "description": "Recommended number of sets (always 3 for hypertrophy)."},
            "Reps": {"type": "STRING", "description": "Recommended repetition range (e.g., '8-12')."},
            "Safety Cue": {"type": "STRING", "description": "A critical safety tip or form cue."},
            "Steps to Perform": {"type": "STRING", "description": "A 3-step instruction on how to perform the exercise. Use periods to separate steps."},
            "Available Equipment": {"type": "STRING", "description": "The equipment actually used for this exercise."},
        },
        "required": ["Exercise Name", "Target Region", "Sets", "Reps", "Safety Cue", "Steps to Perform", "Available Equipment"]
    }
    
    # 2. Construct the prompt
    user_prompt = f"""
    You are an expert fitness coach. The automatic plan generator failed to find a suitable exercise for the user's profile.
    
    GOAL: {profile['primary_goal']} (MUST use RPE 7-9 intensity, 3 sets, 8-15 reps).
    MISSING CATEGORY: {res_cat}
    USER LEVEL: {profile['fitness_level']}
    AVAILABLE EQUIPMENT: {available_equipment}
    
    Please invent a single, highly effective, compound exercise that fits these strict criteria and uses the available equipment. 
    Ensure the 'Sets' value is 3 and the 'Reps' value is a range (e.g., '8-12'). The 'Steps to Perform' must be a single string containing 3 steps separated by periods.
    """
    
    # 3. Construct the API payload
    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "config": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
        "systemInstruction": {
            "parts": [{"text": "You are a fitness expert focused on safety and hypertrophy. Respond only with the requested JSON object."}]
        }
    }

    # 4. Make the API request with exponential backoff (for reliability)
    max_retries = 3
    delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", 
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload),
                                     timeout=15)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()
            
            # Extract text (JSON string) from the response structure
            json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            if json_text:
                ai_data = json.loads(json_text)
                
                # Add mandatory fields not in the prompt/schema
                ai_data['Resistance_Category'] = res_cat
                ai_data['Concept_Group'] = ai_data['Exercise Name'].split(' ')[0].lower()
                ai_data['Category'] = 'AI Generated - Resistance'
                ai_data['RPE'] = '7-9' # Enforce RPE 7-9 on the AI output
                ai_data['Health Benefit'] = f"AI Substitution for {res_cat}"
                ai_data['Complexity_Level'] = profile['max_complexity'] # Match user's max level
                
                return ai_data
            
        except requests.exceptions.HTTPError as e:
            st.warning(f"AI Fallback Attempt {attempt + 1} failed (HTTP Error: {e.response.status_code}). Retrying...")
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            st.warning(f"AI Fallback Attempt {attempt + 1} failed (Connection/Parse Error: {e}). Retrying...")

        if attempt < max_retries - 1:
            st.info(f"Waiting {delay}s before retry...")
            time.sleep(delay)
            delay *= 2 
        else:
            st.error("AI Fallback failed after multiple attempts. Proceeding without substitution.")
            return None

def generate_workout_plan(df_master: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Generates the full weekly plan with day-wise exercises and structure.
    Implements Tier 4 (AI Fallback) when the resistance pool is empty.
    """
    
    global used_concept_groups_A
    global used_concept_groups_B

    # Reset globals for a new plan generation
    used_concept_groups_A = set() 
    used_concept_groups_B = set()
    
    # --- STEP 1: Filter Master Data and Segregate Pools ---
    
    df_all_filtered = filter_and_select_exercises(df_master, profile)
    
    if df_all_filtered.empty:
        # Check here only if the *entire* filtered pool is empty (Mobility + Resistance)
        return {"Error": pd.DataFrame()}

    
    # Segregate the single filtered pool into two clean, mutually exclusive pools
    df_resistance = df_all_filtered[df_all_filtered['Resistance_Category'].isin(RESISTANCE_CATS)].copy()
    df_mobility = df_all_filtered[~df_all_filtered['Resistance_Category'].isin(RESISTANCE_CATS)].copy()

    # --- TIER 4: AI FALLBACK CHECK (Only runs if CSV fails completely) ---
    
    if df_resistance.empty:
        st.warning("⚠️ **Tier 4 Fallback Triggered:** CSV filtering failed to find any strength exercises. Requesting AI substitution...")
        
        # We need at least one Push, one Pull, and one Lower to start a plan.
        missing_categories = ['Upper Body Push', 'Upper Body Pull', 'Lower Body']
        ai_substitutions = []
        
        # Generate one substitution for the most critical missing resistance category (e.g., Push)
        for cat in missing_categories:
            ai_data = generate_ai_exercise(profile, cat)
            if ai_data:
                ai_substitutions.append(pd.DataFrame([ai_data]))
                st.success(f"✅ AI successfully generated **{ai_data['Exercise Name']}** for {cat}.")
                break 
        
        if ai_substitutions:
            df_resistance = pd.concat([df_resistance] + ai_substitutions).reset_index(drop=True)
            # Add the AI resistance exercise to the working pool
            df_working = pd.concat([df_all_filtered, df_resistance.tail(len(ai_substitutions))]).drop_duplicates(subset=['Exercise Name']).reset_index(drop=True)
        else:
            return {"Error": pd.DataFrame()}
            
    # Use the dedicated resistance pool from now on
    df_working = df_all_filtered.reset_index(drop=True)


    # --- STEP 2: Determine Volume and Targets ---
    
    session_counts = get_session_counts(profile['session_duration'])
    target_main_count = session_counts['main_count'] # 5, 7, 9, or 11
    target_warmup_count = session_counts['warmup_count'] # 3
    target_cooldown_count = session_counts['cooldown_count'] # 2
    
    # Define required counts for balanced Full Body split (Base Targets)
    if target_main_count >= 9:
        if target_main_count == 9: base_targets = {'Upper Body Push': 2, 'Upper Body Pull': 2, 'Lower Body': 3, 'Core': 2}
        elif target_main_count == 11: base_targets = {'Upper Body Push': 3, 'Upper Body Pull': 3, 'Lower Body': 3, 'Core': 2}
    elif target_main_count == 7:
        base_targets = {'Upper Body Push': 2, 'Upper Body Pull': 2, 'Lower Body': 2, 'Core': 1}
    else: # 5 exercises (min)
        base_targets = {'Upper Body Push': 1, 'Upper Body Pull': 1, 'Lower Body': 2, 'Core': 1}
    
    training_days = profile['days_per_week']
    split_rules = get_training_split(len(training_days), profile['fitness_level'])
    
    workout_plan = {}
    
    # Pre-define workout specific targets for the A-B-A split (for structural balance/focus)
    targets_A = base_targets.copy() # Lower Focus (e.g., 3 Lower)
    targets_B = base_targets.copy() # Upper Focus (Shift 1 Lower exercise to 1 Upper Push/Pull)
    
    if targets_A.get('Lower Body', 0) > 1:
        targets_B['Lower Body'] = targets_B.get('Lower Body') - 1
        targets_B['Upper Body Push'] = targets_B.get('Upper Body Push', 0) + 1 # Increase Upper Push

    workout_targets = {}
    for rule in split_rules:
        if rule == "Full-Body A": workout_targets[rule] = targets_A
        elif rule == "Full-Body B": workout_targets[rule] = targets_B
        elif rule == "Active Recovery": workout_targets[rule] = {}
        else: workout_targets[rule] = base_targets
    
    
    # --- STEP 3: Generate Daily Plans ---
    
    for day_index, (day, rule) in enumerate(zip(training_days, split_rules)):
        
        current_targets = workout_targets.get(rule, {})
        
        # --- Variety Setup (Crucial for A-B Split) ---
        if rule == "Full-Body A":
            filter_concepts = used_concept_groups_B 
            track_concepts = used_concept_groups_A 
        elif rule == "Full-Body B":
            filter_concepts = used_concept_groups_A 
            track_concepts = used_concept_groups_B 
        else:
            filter_concepts = used_concept_groups_A.union(used_concept_groups_B) 
            track_concepts = used_concept_groups_A
            
        # 1. Warm-up (Select from strictly mobility pool)
        warmup_pool = df_mobility[~df_mobility['Concept_Group'].isin(filter_concepts)].copy()
        if warmup_pool.empty: warmup_pool = df_mobility.copy() 

        warmup_selection = warmup_pool.sample(min(target_warmup_count, len(warmup_pool)), replace=False, random_state=abs(42 + day_index) % (2**32 - 1))
        warmup_selection = warmup_selection.assign(Part='Warm-Up', Order=range(1, len(warmup_selection) + 1))
        warmup_selection['Sets'] = warmup_selection['Sets'].fillna(1)
        warmup_selection['RPE'] = warmup_selection['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{min(1, int(m.group(1)))}-{min(4, int(m.group(2)))}", str(x)))


        # 2. Main Workout (Strict Balanced Selection from Resistance pool)
        if rule == "Active Recovery":
            main_selection = pd.DataFrame()
        else:
            # Use the dedicated resistance pool here
            main_pool = df_resistance.copy() 
            
            # CRITICAL HYPERTROPHY PARAMETER ENFORCEMENT (Final output display fix)
            if profile['primary_goal'] in ["Muscle Gain (Hypertrophy)", "Strength Gain"]:
                # Ensure every exercise selected has hypertrophy parameters
                main_pool['Sets'] = main_pool['Sets'].apply(lambda x: max(3, int(x)) if pd.notna(x) else 3)
                main_pool['Reps'] = main_pool['Reps'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{max(8, int(m.group(1)))}-{min(15, int(m.group(2)))}", str(x)))
                main_pool['RPE'] = main_pool['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{max(7, int(m.group(1)))}-{min(9, int(m.group(2)))}", str(x)))


            main_selection_list = []
            current_day_names = set() 
            
            # --- Tier 1 Selection (Mandatory Resistance Guarantee) ---
            for res_cat, count in current_targets.items():
                if count == 0: continue
                
                cat_pool = main_pool[main_pool['Resistance_Category'] == res_cat].copy()
                
                # FIX: Strictly exclude mobility exercises by name if they somehow slipped into the resistance pool
                mobility_names = df_mobility['Exercise Name'].unique()
                cat_pool = cat_pool[~cat_pool['Exercise Name'].isin(mobility_names)]

                cat_pool = cat_pool[~cat_pool['Concept_Group'].isin(filter_concepts)]
                cat_pool = cat_pool[~cat_pool['Exercise Name'].isin(current_day_names)]
                selection_n = min(count, len(cat_pool))
                
                # CRITICAL: If Tier 1 fails to find the required count, we must accept what we can get for balance
                # BUT WE CANNOT PROCEED IF COUNT IS 0 AND IT IS A PUSH/PULL/LOWER CATEGORY
                if selection_n > 0:
                    seed_val = abs(day_index + hash(res_cat)) % (2**32 - 1)
                    selected = cat_pool.sample(selection_n, replace=False, random_state=seed_val)
                    current_day_names.update(selected['Exercise Name'].tolist())
                    main_selection_list.append(selected)
                elif count > 0 and res_cat in ['Upper Body Push', 'Upper Body Pull', 'Lower Body']:
                    # Tier 2 Fallback for balance: relax concept filter but keep name uniqueness
                    cat_pool_relaxed = main_pool[main_pool['Resistance_Category'] == res_cat].copy()
                    cat_pool_relaxed = cat_pool_relaxed[~cat_pool_relaxed['Exercise Name'].isin(current_day_names)]
                    
                    if not cat_pool_relaxed.empty:
                        selection_n_fallback = min(count, len(cat_pool_relaxed))
                        seed_val = abs(day_index + hash(res_cat) + 50) % (2**32 - 1)
                        selected = cat_pool_relaxed.sample(selection_n_fallback, replace=False, random_state=seed_val)
                        current_day_names.update(selected['Exercise Name'].tolist())
                        main_selection_list.append(selected)


            if main_selection_list:
                main_selection = pd.concat(main_selection_list).drop_duplicates(subset=['Exercise Name'])
                track_concepts.update(main_selection['Concept_Group'].tolist())
                
                # --- Tier 3: Final Volume Fill ---
                while len(main_selection) < target_main_count:
                    fill_needed = target_main_count - len(main_selection)
                    reusable_pool = main_pool[~main_pool['Exercise Name'].isin(main_selection['Exercise Name'])] 
                    
                    if reusable_pool.empty: break
                        
                    reused_selection = reusable_pool.sample(min(fill_needed, len(reusable_pool)), replace=False, random_state=abs(day_index + len(main_selection) + 700) % (2**32 - 1))
                    main_selection = pd.concat([main_selection, reused_selection]).drop_duplicates(subset=['Exercise Name'])

                # Finalize selection and shuffle
                main_selection = main_selection.head(target_main_count) 
                final_shuffle_seed = abs(day_index + 100) % (2**32 - 1)
                main_selection = main_selection.sample(frac=1, random_state=final_shuffle_seed) 
                main_selection = main_selection.assign(Part='Main Workout', Order=range(1, len(main_selection) + 1))
            else:
                main_selection = pd.DataFrame() 
                
        # 3. Cool-Down (Select from strictly mobility pool)
        cooldown_pool = df_mobility[~df_mobility['Concept_Group'].isin(track_concepts)].copy()
        if cooldown_pool.empty: cooldown_pool = df_mobility.copy() 

        cooldown_selection = cooldown_pool.sample(min(target_cooldown_count, len(cooldown_pool)), replace=False, random_state=abs(42 + day_index * 2) % (2**32 - 1))
        cooldown_selection = cooldown_selection.assign(Part='Cool-Down', Order=range(1, len(cooldown_selection) + 1))
        
        cooldown_selection['Sets'] = cooldown_selection['Sets'].fillna(1)
        cooldown_selection['RPE'] = cooldown_selection['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{min(1, int(m.group(1)))}-{min(3, int(m.group(2)))}", str(x)))
        
        # Combine
        daily_plan = pd.concat([warmup_selection, main_selection, cooldown_selection]).reset_index(drop=True)
        
        # Demographic Adjustments (ACSM guideline implementation)
        if profile['age'] >= 60 or (profile['bmi'] is not None and profile['bmi'] >= 30):
            daily_plan['RPE'] = daily_plan['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{max(1, int(m.group(1))-1)}-{max(2, int(m.group(2))-1)}", x))
            daily_plan['Safety Cue'] = daily_plan['Safety Cue'].fillna('').apply(lambda x: f"{x} (Prioritize stability and balance.)" if "(Prioritize stability and balance.)" not in x else x)
        
        if profile['gender'] == 'Female':
            daily_plan['RPE'] = daily_plan['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{m.group(1)}-{max(2, int(m.group(2))-1)}", x))

        workout_plan[day] = daily_plan
        
        # FIX: Only attempt to update concept groups if main_selection is NOT empty
        if not main_selection.empty:
            if rule == "Full-Body A":
                used_concept_groups_A.update(main_selection['Concept_Group'].tolist())
            elif rule == "Full-Body B":
                used_concept_groups_B.update(main_selection['Concept_Group'].tolist())
        
    return workout_plan

# ============ DISPLAY FUNCTIONS (Strict Custom Format) ============

def display_exercise_plan(workout_plan: Dict[str, pd.DataFrame], profile: Dict[str, Any]):
    """Displays the final exercise plan in the requested detailed custom format for ALL exercises."""
    
    if "Error" in workout_plan:
        st.error("❌ No exercises matched your profile criteria. Try adjusting your selections (especially equipment or fitness level).")
        return

    st.markdown("---")
    st.header(f"👋 Welcome, {profile.get('name', 'User')}!")
    st.subheader("Your Personalized Fitness Plan is Ready")
    
    # Header Info
    st.markdown(f"""
        📅 Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        🎯 Goal: **{profile['primary_goal']}** | 
        💪 Level: **{profile['fitness_level']}**
    """)
    
    st.markdown("\n\n")
    st.subheader("📅 Your Weekly Workout Schedule")

    for day, df_plan in workout_plan.items():
        st.markdown(f"## 📋 {day} Workout")
        
        main_df = df_plan[df_plan['Part'] == 'Main Workout']
        focus = "Full Body"
        if not main_df.empty:
            # Base focus on the Resistance_Category count for true focus indication
            focus_counts = main_df['Resistance_Category'].value_counts()
            if not focus_counts.empty:
                primary_focus = focus_counts.index[0]
                focus = f"{focus} ({primary_focus.replace('Upper Body ', '').replace('Lower Body', 'Lower')} Focus)"

        st.markdown(f"**{day} – {focus}**")
        
        exercise_count = 0
        
        for part, group in df_plan.groupby('Part', sort=False):
            
            time_estimate = " (5-7 minutes)" if part in ['Warm-Up', 'Cool-Down'] else ""
            st.markdown(f"### {part}{time_estimate}")
            
            
            for idx, row in group.iterrows():
                exercise_count += 1
                
                # Retrieve details
                sets = row.get('Sets', 1)
                reps = row.get('Reps', 'N/A')
                rpe = row.get('RPE', 'N/A')
                rest = row.get('Rest Intervals', 'N/A')
                
                # Format RPE: ensure it's displayed ascending (e.g., 7-9)
                rpe_match = re.match(r'(\d+)-(\d+)', str(rpe))
                if rpe_match:
                    rpe_start = int(rpe_match.group(1))
                    rpe_end = int(rpe_match.group(2))
                    rpe = f"{min(rpe_start, rpe_end)}-{max(rpe_start, rpe_end)}"

                # Title
                exercise_name = row['Exercise Name']
                if row.get('Category') == 'AI Generated - Resistance':
                    exercise_name = f"🤖 {exercise_name} (AI Substitution)"
                
                st.markdown(f"**{exercise_count}. {exercise_name}**")
                
                # Benefit
                st.markdown(f"**Benefit**: {row.get('Health Benefit', 'N/A')}")
                
                # How to Perform (numbered list format)
                st.markdown("**How to Perform:**")
                
                raw_instructions = row.get('Steps to Perform', 'N/A').strip()
                steps = [s.strip() for s in re.split(r'\.\s*', raw_instructions) if s.strip()]
                
                # Build the instruction block with fixed indentation
                step_markdown = ""
                step_number = 1
                for step_content in steps:
                    
                    step_content = re.sub(r'^\d+\.?\s*', '', step_content).strip()
                    
                    if step_content:
                        if not step_content.endswith('.'):
                            step_content += '.'
                            
                        # Ensure proper indentation and clean sequential list
                        step_markdown += f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{step_number}. {step_content}<br>"
                        step_number += 1
                
                st.markdown(step_markdown, unsafe_allow_html=True)
                        
                # Details (no columns used, strictly sequential markdown lines)
                st.markdown(f"**Sets**: {sets}")
                st.markdown(f"**Reps**: {reps}")
                st.markdown(f"**Intensity**: RPE {rpe}")
                st.markdown(f"**Rest**: {rest}")
                st.markdown(f"**Equipment**: {row.get('Available Equipment', 'N/A')}")
                st.markdown(f"**Safety Cue**: {row.get('Safety Cue', 'N/A')}")
                
                st.markdown("\n") # Add extra line after each exercise
            
            st.markdown("---")

# ============ MAIN APP ============
def main():
    """Main application function."""
    
    st.set_page_config(page_title="FriskaAI Fitness Coach", page_icon="💪", layout="wide")
    st.title("💪 FriskaAI Fitness Coach (Hybrid Model)")
    st.markdown("Get a personalized, ACSM-aligned workout plan, augmented by AI for consistency and customization.")
    
    df_exercise = load_exercise_data()
    if df_exercise.empty:
        # Stop execution if data failed to load
        return
    
    # Initialize session state with all required fields
    if 'profile_state' not in st.session_state:
        st.session_state.profile_state = {
            'name': 'Gnyan', 'age': 30, 'gender': 'Male', 
            'unit_system': 'Metric (kg, cm)', 'weight_kg': 70.0, 'height_cm': 170.0, 'bmi': 24.2,
            'primary_goal': 'Muscle Gain (Hypertrophy)', 'secondary_goal': 'None',
            'fitness_level': 'Level 3 – Moderate / Independent', 
            'medical_conditions': ["None"],
            'physical_limitations': '',
            'days_per_week': ["Monday", "Wednesday", "Friday"], 
            'session_duration': '30-45 minutes',
            'available_equipment': ["Bodyweight Only", "Dumbbells", "Stable Chair", "Yoga Mat"], 
            'workout_location': 'Home',
        }
    
    profile = st.session_state.profile_state
    
    # ============ THE FORM ============
    with st.form("fitness_form"):
        
        # 1. Basic Info
        st.subheader("📋 Basic Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            name = st.text_input("Name *", value=profile.get('name', ''), placeholder="Enter your name")
            age = st.number_input("Age *", min_value=13, max_value=100, value=profile.get('age', 30))
        
        with col2:
            gender = st.selectbox("Gender *", ["Male", "Female", "Other"], 
                                 index=["Male", "Female", "Other"].index(profile.get('gender', 'Male')))
            workout_location = st.selectbox("Workout Location *", LOCATION_OPTIONS,
                                            index=LOCATION_OPTIONS.index(profile.get('workout_location', 'Home')))

        with col3:
            unit_system = st.radio("Units *", ["Metric (kg, cm)", "Imperial (lbs, in)"], 
                                  index=["Metric (kg, cm)", "Imperial (lbs, in)"].index(profile.get('unit_system', 'Metric (kg, cm)')))
            
        col_w, col_h, col_bmi = st.columns(3)
        with col_w:
            weight_kg = 0.0
            if unit_system == "Metric (kg, cm)":
                weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=profile.get('weight_kg', 70.0))
            else:
                weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=profile.get('weight_kg', 70.0) / 0.453592)
                weight_kg = weight_lbs * 0.453592
        
        with col_h:
            height_cm = 0.0
            if unit_system == "Metric (kg, cm)":
                height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=profile.get('height_cm', 170.0))
            else:
                height_in = st.number_input("Height (in) *", min_value=39.0, max_value=98.0, value=profile.get('height_cm', 170.0) / 2.54)
                height_cm = height_in * 2.54
                
        with col_bmi:
            current_bmi = calculate_bmi(weight_kg, height_cm)
            bmi_display = f"{current_bmi:.1f}" if current_bmi else "N/A"
            bmi_type = ""
            if current_bmi:
                if current_bmi < 18.5: bmi_type = " (Underweight)"
                elif current_bmi < 25: bmi_type = " (Normal)"
                elif current_bmi < 30: bmi_type = " (Overweight)"
                else: bmi_type = " (Obese)"
            st.info(f"📊 Your BMI: {bmi_display}{bmi_type}")

        # 2. Fitness Goals & Level
        st.subheader("🎯 Fitness Goals & Level")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            primary_goal = st.selectbox("Primary Goal *", GOAL_OPTIONS, 
                                       index=GOAL_OPTIONS.index(profile.get('primary_goal', 'Muscle Gain (Hypertrophy)')))
        
        with col_g2:
            secondary_options = ["None"] + [g for g in GOAL_OPTIONS if g != primary_goal]
            secondary_goal = st.selectbox("Secondary Goal (Optional)", secondary_options, 
                                         index=secondary_options.index(profile.get('secondary_goal', 'None')))
        
        fitness_level = st.selectbox("Fitness Level *", list(FITNESS_LEVELS.keys()), 
                                    index=list(FITNESS_LEVELS.keys()).index(profile.get('fitness_level', 'Level 3 – Moderate / Independent')))
        
        level_info = FITNESS_LEVELS[fitness_level]
        st.info(f"**{fitness_level}**: {level_info['description']} | **RPE**: {level_info['rpe_range']}")
        
        # 3. Health Screening
        st.subheader("🏥 Health Screening")
        medical_conditions = st.multiselect("Medical Conditions * (Used for exercise exclusion)", MEDICAL_CONDITIONS, 
                                           default=profile.get('medical_conditions', ["None"]))
        
        st.warning("⚠️ **Physical Limitations** - Describe ANY injuries, pain or movement restrictions")
        physical_limitations = st.text_area("Physical Limitations (Important for Safety) *", 
                                           value=profile.get('physical_limitations', ''),
                                           placeholder="E.g., 'Previous right knee surgery - avoid deep squats'",
                                           height=100)
        
        # 4. Training Schedule & Equipment
        st.subheader("💪 Training Schedule & Equipment")
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            days_per_week = st.multiselect("Preferred Training Days *", 
                                          ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                          default=profile.get('days_per_week', ["Monday", "Wednesday", "Friday"]))
            session_duration = st.selectbox("Preferred Session Duration *", 
                                           list(DURATION_MAP.keys()),
                                           index=list(DURATION_MAP.keys()).index(profile.get('session_duration', '30-45 minutes')))
        
        with col_t2:
            equipment = st.multiselect("Select all available equipment:", EQUIPMENT_OPTIONS, 
                                  default=profile.get('available_equipment', ["Bodyweight Only", "Dumbbells", "Stable Chair", "Yoga Mat"]))
            if not equipment: equipment = ["Bodyweight Only"]
            
        st.markdown("---")
        
        submit_clicked = st.form_submit_button("🚀 Generate My Exercise Plan (ACSM-Aligned)", 
                                              use_container_width=True, type="primary")
        
        if submit_clicked:
            if df_exercise.empty:
                st.error("Cannot generate plan: The exercise database failed to load. Please check the file path.")
            elif not name or len(name.strip()) < 2:
                st.error("❌ Please enter your name.")
            elif not days_per_week:
                st.error("❌ Please select at least one training day.")
            elif weight_kg <= 0 or height_cm <= 0:
                st.error("❌ Please ensure valid weight and height inputs.")
            else:
                profile_data = {
                    'name': name, 'age': age, 'gender': gender, 'unit_system': unit_system,
                    'weight_kg': weight_kg, 'height_cm': height_cm, 'bmi': current_bmi,
                    'primary_goal': primary_goal, 'secondary_goal': secondary_goal,
                    'fitness_level': fitness_level, 'medical_conditions': medical_conditions,
                    'physical_limitations': physical_limitations,
                    'days_per_week': days_per_week, 'session_duration': session_duration,
                    'available_equipment': equipment, 'workout_location': workout_location,
                }
                st.session_state.profile_state = profile_data
                
                st.markdown("## 🔍 Analyzing Profile and Generating Plan...")
                with st.spinner("Filtering, substituting, and structuring your plan based on ACSM guidelines..."):
                    workout_plan = generate_workout_plan(df_exercise, profile_data)
                    display_exercise_plan(workout_plan, profile_data)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>⚠️ Medical Disclaimer:</strong> This plan is for informational purposes only and is not medical advice. 
        Consult a healthcare professional before beginning any new exercise regimen.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == '__main__':
    main()