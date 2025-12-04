import streamlit as st
import requests
from typing import Dict, List, Optional, Set
import re
from datetime import datetime

# ============ CONFIGURATION ============
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(
    page_title="FriskaAI Fitness Coach",
    page_icon="💪",
    layout="wide"
)

# ============ MEDICAL CONDITIONS DATABASE ============
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

# ============ CONDITION-SPECIFIC GUIDELINES DATABASE ============
CONDITION_GUIDELINES_DB = {
    "Hypertension": {
        "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing without control, breath-holding during lifts",
        "modified": "Controlled breathing, moderate resistance, continuous breathing pattern, avoid maximal effort",
        "intensity": "RPE 4-6, avoid RPE >7",
        "notes": "Monitor for dizziness, stop if experiencing headache or visual changes. Blood pressure should be <160/100 before exercise."
    },
    "Type 2 Diabetes": {
        "contraindicated": "High-intensity intervals without medical clearance, prolonged fasting exercise, exercises causing severe blood sugar fluctuations",
        "modified": "Moderate-intensity steady state, check blood glucose pre/post workout, post-meal walking encouraged",
        "intensity": "RPE 5-7, progress gradually",
        "notes": "Have fast-acting carbs available, monitor for hypoglycemia signs (shakiness, confusion, sweating). Ideal range: 100-250 mg/dL before exercise."
    },
    "Osteoarthritis": {
        "contraindicated": "High-impact jumping, deep squats with pain, excessive joint loading, running on hard surfaces",
        "modified": "Low-impact alternatives (swimming, cycling), partial range if painful, aquatic exercise preferred, use of resistance bands",
        "intensity": "RPE 3-6, pain-free range only",
        "notes": "Some mild discomfort acceptable, sharp pain is a stop signal. Warmth and gentle movement often helpful."
    },
    "Osteoporosis": {
        "contraindicated": "Spinal flexion exercises, high-impact if severe, twisting movements under load, forward bending",
        "modified": "Weight-bearing activities, resistance training with proper form, balance work, spine extension exercises",
        "intensity": "RPE 4-6, progressive loading",
        "notes": "Focus on bone-strengthening exercises, avoid fall risk scenarios. Consult physician about bone density status."
    },
    "Chronic Lower Back Pain": {
        "contraindicated": "Loaded spinal flexion, unsupported twisting, heavy deadlifts initially, sit-ups with feet anchored",
        "modified": "Core stabilization, neutral spine movements, progressive loading, bird dogs, dead bugs, planks",
        "intensity": "RPE 3-5 initially, pain-free movement only",
        "notes": "Pain centralization (moving toward spine) is good, peripheralization (moving down leg) requires modification or stop."
    },
    "Asthma": {
        "contraindicated": "Cold air exposure, continuous high-intensity cardio without breaks, exercises in high-pollen environments",
        "modified": "Interval training with rest periods, swimming (warm humid air), controlled breathing exercises, gradual warm-up",
        "intensity": "RPE 5-7, with frequent breaks",
        "notes": "Keep rescue inhaler accessible. Use preventive inhaler 15-30 min before exercise if prescribed. Stop if wheezing occurs."
    },
    "Coronary Artery Disease": {
        "contraindicated": "Maximal effort exercises, isometric exercises, sudden intense exertion",
        "modified": "Supervised moderate aerobic exercise, gradual progression, extended warm-up and cool-down",
        "intensity": "RPE 3-5, medical clearance required",
        "notes": "Stop immediately if chest pain, unusual shortness of breath, or dizziness occurs. Medical supervision recommended."
    },
    "COPD": {
        "contraindicated": "High-intensity continuous cardio, exercises causing severe breathlessness, cold air exposure",
        "modified": "Interval training, pursed-lip breathing, upper body exercises with breathing coordination",
        "intensity": "RPE 3-6, ability to speak in short sentences",
        "notes": "Use supplemental oxygen if prescribed. Focus on breathing techniques and pacing."
    }
}
class FitnessAdvisor:
    """Enhanced fitness planning engine with refined expert-based prompting structure"""
    
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.weekly_exercises_used = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
        
        # Goal-specific exercise logic
        self.goal_programming_guidelines = {
            "Weight Loss": {
                "priority": "Low to moderate-intensity cardio + resistance for large muscle groups",
                "cardio_resistance_ratio": {
                    1: {"cardio": 1, "strength": 0},
                    2: {"cardio": 1, "strength": 1},
                    3: {"cardio": 2, "strength": 1},
                    4: {"cardio": 2, "strength": 2},
                    5: {"cardio": 3, "strength": 2},
                    6: {"cardio": 3, "strength": 3},
                    7: {"cardio": 3, "strength": 3, "recovery": 1}
                },
                "rpe_range": "5-7",
                "rep_range": "12-20",
                "rest": "30-45 seconds"
            },
            "Muscle Gain": {
                "priority": "Progressive overload resistance training, controlled tempo",
                "split_type": {
                    1: "Full Body",
                    2: "Full Body x2",
                    3: "Full Body x3",
                    4: "Upper/Lower Split",
                    5: "Push/Pull/Legs",
                    6: "Push/Pull/Legs x2",
                    7: "Push/Pull/Legs x2 + Recovery"
                },
                "rpe_range": "6-8",
                "rep_range": "6-12",
                "rest": "60-90 seconds"
            },
            "Increase Overall Strength": {
                "priority": "Compound lifts, progressive loading, mobility work",
                "focus": "Heavy compound movements + accessory work",
                "rpe_range": "7-9",
                "rep_range": "4-8",
                "rest": "90-180 seconds"
            },
            "Improve Cardiovascular Fitness": {
                "priority": "Aerobic/interval protocols, recovery days, low-impact for older/obese",
                "intensity": "60-80% max HR",
                "rpe_range": "5-8",
                "modality": "Continuous or interval training"
            },
            "Improve Flexibility & Mobility": {
                "priority": "Stretching, joint mobility, dynamic ROM, breathing control",
                "rpe_range": "3-5",
                "hold_duration": "30-60 seconds per stretch",
                "focus": "Full range of motion"
            },
            "Rehabilitation & Injury Prevention": {
                "priority": "Corrective exercises, stability, low-load resistance",
                "rpe_range": "3-5",
                "rep_range": "10-15",
                "rest": "60-90 seconds",
                "exclude": "High-impact, ballistic movements"
            },
            "Improve Posture and Balance": {
                "priority": "Core activation, mobility, balance, proprioceptive drills",
                "rpe_range": "4-6",
                "focus": "Postural muscles, single-leg work"
            },
            "General Fitness": {
                "priority": "Balanced approach: cardio, strength, flexibility, balance",
                "rpe_range": "5-7",
                "rep_range": "10-15",
                "rest": "45-60 seconds"
            }
        }


        
    
    def reset_weekly_tracker(self):
        """Reset exercise tracker for new week generation"""
        self.weekly_exercises_used = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
    
    def _apply_demographic_adjustments(self, user_profile: Dict) -> Dict:
        """
        Apply automatic demographic and gender-based adjustments
        Returns adjusted parameters
        """
        adjustments = {
            "intensity_modifier": 1.0,
            "volume_modifier": 1.0,
            "complexity_reduction": False,
            "special_considerations": []
        }
        
        age = user_profile.get("age", 30)
        bmi = user_profile.get("bmi", 22)
        gender = user_profile.get("gender", "Other").lower()
        
        # Age-based adjustments (≥60 years)
        if age >= 60:
            adjustments["intensity_modifier"] *= 0.75
            adjustments["volume_modifier"] *= 0.80
            adjustments["special_considerations"].extend([
                "Reduce overall intensity and volume",
                "Prioritize balance and mobility work",
                "Use joint-friendly movements",
                "Extended warm-up required (10+ minutes)"
            ])
        
        # BMI-based adjustments (≥30 = Obese)
        if bmi >= 30:
            adjustments["intensity_modifier"] *= 0.75
            adjustments["special_considerations"].extend([
                "Emphasize low-impact exercises",
                "Gradual progression required",
                "Avoid high-impact jumping movements",
                "Monitor joint stress"
            ])
        
        # Gender-based adjustments (Female)
        if gender == "female":
            adjustments["intensity_modifier"] *= 0.80
            adjustments["volume_modifier"] *= 0.85
            adjustments["complexity_reduction"] = True
            adjustments["special_considerations"].append(
                "Exercise complexity adjusted for fitness level"
            )
        
        return adjustments
    
    def _determine_workout_distribution(self, days_per_week: int, fitness_level: str, primary_goal: str) -> Dict:
        """
        Determine workout distribution based on frequency, level, and goal
        Returns structure for the week
        """
        level_num = self._extract_level_number(fitness_level)
        
        distribution_rules = {
            1: {
                "structure": "Single Full-Body",
                "description": "One comprehensive full-body workout aligned with goal"
            },
            2: {
                "structure": "Two Full-Body" if level_num <= 3 else "Two Full-Body (Different)",
                "description": "Two full-body sessions. Levels 1-3 can repeat; Levels 4-5 use different exercises"
            },
            3: {
                "structure": "Three Full-Body" if level_num <= 2 else "Two Same + One Different",
                "description": "Levels 1-2: repeat all. Levels 3-5: Mon/Fri same, Wed different"
            },
            4: {
                "structure": "2 Days Same + 2 Days Same (Split)",
                "description": "Category-based split (e.g., Stability, Strength, Core, Rehab)",
                "split_categories": self._get_split_categories(primary_goal, 4)
            },
            5: {
                "structure": "3 Days Same + 2 Days Same (Split)",
                "description": "Goal and category-based split",
                "split_categories": self._get_split_categories(primary_goal, 5)
            },
            6: {
                "structure": "3 Days Same + 3 Days Same (Split)",
                "description": "Category-based split & progression",
                "split_categories": self._get_split_categories(primary_goal, 6)
            },
            7: {
                "structure": "3 Days Same + 3 Days Same + 1 Active Recovery",
                "description": "Mid-week active recovery (mobility, stretching, light walk)",
                "recovery_day": "Wednesday or Thursday"
            }
        }
        
        return distribution_rules.get(days_per_week, distribution_rules[3])
    
    def _get_split_categories(self, primary_goal: str, days: int) -> List[str]:
        """Get appropriate training split categories based on goal and frequency"""
        
        if "Muscle Gain" in primary_goal or "Strength" in primary_goal:
            if days == 4:
                return ["Upper Body Strength", "Lower Body Strength", "Upper Body Hypertrophy", "Lower Body Hypertrophy"]
            elif days == 5:
                return ["Push", "Pull", "Legs", "Push", "Pull"]
            elif days == 6:
                return ["Push", "Pull", "Legs", "Push", "Pull", "Legs"]
        
        elif "Weight Loss" in primary_goal:
            if days == 4:
                return ["Cardio + Core", "Full Body Strength", "Cardio + Core", "Full Body Strength"]
            elif days == 5:
                return ["Cardio", "Strength", "Cardio", "Strength", "Core + Mobility"]
            elif days == 6:
                return ["Cardio", "Upper Strength", "Lower Strength", "Cardio", "Full Body", "Core + Mobility"]
        
        else:  # General Fitness or other goals
            if days == 4:
                return ["Strength + Stability", "Cardio + Core", "Strength + Stability", "Cardio + Core"]
            elif days == 5:
                return ["Strength", "Cardio", "Core + Balance", "Strength", "Flexibility"]
            elif days == 6:
                return ["Upper Strength", "Cardio", "Lower Strength", "Core", "Full Body", "Mobility"]
        
        return ["Full Body"] * days
    
    def _extract_level_number(self, fitness_level: str) -> int:
        """Extract numeric level from fitness level string"""
        if "Level 1" in fitness_level or "Assisted" in fitness_level:
            return 1
        elif "Level 2" in fitness_level or "Beginner" in fitness_level:
            return 2
        elif "Level 3" in fitness_level or "Moderate" in fitness_level:
            return 3
        elif "Level 4" in fitness_level or "Active" in fitness_level:
            return 4
        elif "Level 5" in fitness_level or "Advanced" in fitness_level:
            return 5
        return 3  # Default to moderate
    
    def _calculate_session_timing(self, session_duration: str) -> Dict:
        """Calculate time allocation for warm-up, main workout, and cooldown"""
        
        # Extract duration in minutes
        if "15-20" in session_duration or "15-30" in session_duration:
            total_minutes = 20
        elif "20-30" in session_duration:
            total_minutes = 25
        elif "30-45" in session_duration:
            total_minutes = 37
        elif "45-60" in session_duration:
            total_minutes = 52
        elif "60+" in session_duration or "60-90" in session_duration:
            total_minutes = 75
        else:
            total_minutes = 40  # Default
        
        return {
            "total": total_minutes,
            "warmup": round(total_minutes * 0.15),  # 15%
            "main": round(total_minutes * 0.70),    # 70%
            "cooldown": round(total_minutes * 0.15), # 15%
            "warmup_exercises": 3 if total_minutes < 30 else 4,
            "main_exercises": self._calculate_main_exercise_count(total_minutes),
            "cooldown_exercises": 3 if total_minutes < 30 else 4
        }
    
    def _calculate_main_exercise_count(self, total_minutes: int) -> int:
        """Determine number of main exercises based on total session time"""
        if total_minutes <= 25:
            return 4
        elif total_minutes <= 40:
            return 6
        elif total_minutes <= 55:
            return 7
        else:
            return 8
    
    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        workout_category: str = "Full Body",
        is_modification: bool = False,
        modification_request: str = "",
        original_plan_context: str = None
    ) -> str:
        """
        Build ultra-precise system prompt following refined expert guidelines
        """
        
        # Extract profile data
        name = user_profile.get("name", "User")
        age = user_profile.get("age", 30)
        gender = user_profile.get("gender", "Other")
        bmi = user_profile.get("bmi", 22)
        fitness_level = user_profile.get("fitness_level", "Level 3 - Intermediate")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        location = user_profile.get("workout_location", "Home")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        available_equipment = user_profile.get("available_equipment", ["None - Bodyweight Only"])
        physical_limitations = user_profile.get("physical_limitations", "")
        days_per_week = len(user_profile.get("days_per_week", []))
        session_duration = user_profile.get("session_duration", "30-45 minutes")
        
        # Apply demographic adjustments
        adjustments = self._apply_demographic_adjustments(user_profile)
        
        # Get workout distribution structure
        distribution = self._determine_workout_distribution(days_per_week, fitness_level, primary_goal)
        
        # Calculate session timing
        timing = self._calculate_session_timing(session_duration)
        
        # Get goal-specific programming guidelines
        goal_guidelines = self.goal_programming_guidelines.get(primary_goal, self.goal_programming_guidelines["General Fitness"])
        
        # Get fitness level number
        level_num = self._extract_level_number(fitness_level)
        
        # Build comprehensive prompt sections
        prompt_parts = []
        
        # ==================== SECTION 0: IDENTITY & MISSION ====================
        prompt_parts.append("""You are FriskaAI, an expert clinical exercise physiologist (ACSM-CEP) with 15+ years of experience in personalized, evidence-based program design.

**YOUR MISSION:** Create a workout plan that strictly follows ACSM guidelines and prioritizes in this exact order:
1. SAFETY (100% - zero contraindicated exercises)
2. EFFECTIVENESS (goal alignment and proper programming)
3. VARIETY (unique exercises within the week)
4. GOAL ALIGNMENT (exercises directly support user's primary goal)

You MUST respond ONLY in English. Every plan you generate will be evaluated by medical professionals.""")
        
        # ==================== SECTION 1: USER PROFILE ====================
        profile_section = f"""

**1. COMPLETE USER PROFILE:**

**Demographics & Physical Data:**
- Name: {name}
- Age: {age} years old | Gender: {gender} | BMI: {bmi}
- Current Fitness Level: {fitness_level} (Level {level_num} of 5)
- Primary Goal: {primary_goal}

**Automatic Demographic Adjustments Applied:**
- Intensity Modifier: {adjustments['intensity_modifier']:.2f}x
- Volume Modifier: {adjustments['volume_modifier']:.2f}x
- Complexity Reduction: {'Yes' if adjustments['complexity_reduction'] else 'No'}
"""
        
        if adjustments['special_considerations']:
            profile_section += f"\n**Special Considerations:**\n"
            for consideration in adjustments['special_considerations']:
                profile_section += f"- {consideration}\n"
        
        profile_section += f"""
**Session Parameters:**
- Session Duration: {session_duration} (Total: {timing['total']} minutes)
- Time Allocation: Warm-up {timing['warmup']}min | Main {timing['main']}min | Cooldown {timing['cooldown']}min
- Exercise Count: {timing['warmup_exercises']} warm-up + {timing['main_exercises']} main + {timing['cooldown_exercises']} cooldown
- Training Frequency: {days_per_week} days per week
- Today's Session: {day_name} (Day {day_index + 1}) - {workout_category}

**Weekly Structure:**
{distribution['description']}

**Workout Environment:**
- Location: {location}
- Available Equipment: {', '.join(available_equipment)}

**Medical & Physical Status:**
- Medical Conditions: {', '.join(medical_conditions)}
- Physical Limitations: {physical_limitations if physical_limitations else 'None reported'}
"""
        
        prompt_parts.append(profile_section)
        
        # ==================== SECTION 2: GOAL-SPECIFIC PROGRAMMING ====================
        goal_section = f"""

**2. GOAL-SPECIFIC PROGRAMMING GUIDELINES (PRIMARY GOAL: {primary_goal}):**

{goal_guidelines.get('priority', 'Follow ACSM general fitness guidelines')}

**Programming Parameters for {primary_goal}:**
"""
        
        if 'rpe_range' in goal_guidelines:
            # Apply demographic intensity modifier
            base_rpe = goal_guidelines['rpe_range']
            goal_section += f"- Target RPE Range: {base_rpe} (adjusted by {adjustments['intensity_modifier']:.2f}x demographic modifier)\n"
        
        if 'rep_range' in goal_guidelines:
            goal_section += f"- Rep Range: {goal_guidelines['rep_range']}\n"
        
        if 'rest' in goal_guidelines:
            goal_section += f"- Rest Periods: {goal_guidelines['rest']}\n"
        
        if primary_goal == "Weight Loss" and days_per_week in goal_guidelines.get('cardio_resistance_ratio', {}):
            ratio = goal_guidelines['cardio_resistance_ratio'][days_per_week]
            goal_section += f"- Workout Distribution: {ratio['cardio']} cardio sessions + {ratio['strength']} strength sessions"
            if 'recovery' in ratio:
                goal_section += f" + {ratio['recovery']} recovery session"
            goal_section += "\n"
        
        if primary_goal == "Muscle Gain" and days_per_week in goal_guidelines.get('split_type', {}):
            split = goal_guidelines['split_type'][days_per_week]
            goal_section += f"- Training Split: {split}\n"
        
        prompt_parts.append(goal_section)
        
        # ==================== SECTION 3: MEDICAL SAFETY PROTOCOL ====================
        safety_section = f"""

**3. MEDICAL SAFETY PROTOCOL (ABSOLUTE PRIORITY - ZERO TOLERANCE):**
"""
        
        if medical_conditions and medical_conditions != ["None"]:
            safety_section += f"""
**CRITICAL:** User has the following medical conditions:
{', '.join(medical_conditions)}

**MANDATORY SAFETY ACTIONS:**
1. Cross-reference EVERY exercise against contraindications for these conditions
2. Automatically EXCLUDE any contraindicated exercises
3. SUBSTITUTE with modified/safer alternatives when needed
4. Apply condition-specific intensity caps (RPE limits)
5. Include targeted safety cues in every exercise

**FAILURE CONDITION:** Including even ONE contraindicated exercise = complete plan rejection

**Condition-Specific Guidelines:**
{self._get_detailed_condition_guidelines(medical_conditions)}
"""
        else:
            safety_section += """
**Standard Safety Protocol:**
- All exercises appropriate for age and fitness level
- Proper progression and form emphasis
- Clear safety cues for injury prevention
- No contraindications identified
"""
        
        prompt_parts.append(safety_section)
        
        # ==================== SECTION 4: FITNESS LEVEL EXERCISE SELECTION ====================
        level_section = f"""

**4. FITNESS LEVEL-BASED EXERCISE SELECTION (LEVEL {level_num}):**

{self._get_fitness_level_exercise_rules(fitness_level, level_num)}

**CRITICAL RULE:** You MUST select exercises that match Level {level_num} complexity.
- If a standard exercise is too advanced, automatically substitute with the appropriate Level {level_num} modification
- Examples provided below show exact exercise progressions by level
"""
        
        prompt_parts.append(level_section)
        
        # ==================== SECTION 5: EQUIPMENT & LOCATION CONSTRAINTS ====================
        equipment_section = f"""

**5. EQUIPMENT & LOCATION CONSTRAINTS:**

**Workout Location: {location}**
**Available Equipment: {', '.join(available_equipment)}**

**ABSOLUTE RULE:** You may ONLY select exercises that can be performed with the equipment listed above and in the specified location.

**Equipment-Appropriate Exercises:**
{self._get_location_equipment_exercises(location, available_equipment, workout_category)}

**If equipment is limited:** Prioritize bodyweight exercises and household items (chair, wall, towel, water bottles).
"""
        
        prompt_parts.append(equipment_section)
        
        # ==================== SECTION 6: EXERCISE VARIETY ENFORCEMENT ====================
        used_exercises = self._format_used_exercises()
        variety_section = f"""

**6. EXERCISE VARIETY REQUIREMENTS (STRICT NO-REPETITION POLICY):**

**This is {day_name} (Day {day_index + 1} of {days_per_week}). ZERO exercise repetition allowed across the week.**

**Exercises Already Used This Week:**
{used_exercises}

**ABSOLUTE RULES:**
- Do NOT use ANY exercise listed above
- Each day must have completely unique exercises
- Similar movements allowed ONLY if significantly modified (e.g., "Standard Push-up" vs "Diamond Push-up" vs "Decline Push-up")
- Use variation strategies: tempo changes, stance modifications, angle changes, unilateral variations

**Weekly Distribution Context:**
{distribution['structure']}
- Today's category/focus: {workout_category}
"""
        
        prompt_parts.append(variety_section)
        
        # ==================== SECTION 7: MANDATORY OUTPUT STRUCTURE ====================
        structure_section = f"""

**7. MANDATORY WORKOUT PLAN STRUCTURE:**

**YOU MUST GENERATE EXACTLY THIS STRUCTURE:**

### {day_name} – {workout_category}

**Warm-Up ({timing['warmup']} minutes) - {timing['warmup_exercises']} movements**

[Movement Name] – [Purpose] – [Duration/Reps] – [Safety Note]
[Movement Name] – [Purpose] – [Duration/Reps] – [Safety Note]
[Movement Name] – [Purpose] – [Duration/Reps] – [Safety Note]
{"[Movement Name] – [Purpose] – [Duration/Reps] – [Safety Note]" if timing['warmup_exercises'] >= 4 else ""}

**Main Workout ({timing['main']} minutes) - {timing['main_exercises']} exercises**

For each exercise, include ALL these fields:

1. [Exercise Name]

**Benefit:** [How this supports {primary_goal}]
**How to Perform:**
1. [Detailed step 1]
2. [Detailed step 2]
3. [Detailed step 3]
4. [Detailed step 4 if needed]

**Sets × Reps:** [Based on goal - use {goal_guidelines.get('rep_range', '10-15')}]
**Intensity:** RPE [Based on goal - target {goal_guidelines.get('rpe_range', '5-7')}]
**Rest:** [{goal_guidelines.get('rest', '45-60 seconds')}]
**Equipment:** [What's needed from available list]
**Safety Cue:** [Specific to user's age/conditions/limitations]

[Repeat for all {timing['main_exercises']} exercises]

**Cool-Down ({timing['cooldown']} minutes) - {timing['cooldown_exercises']} movements**

[Stretch Name] – [Target Area] – [Duration: 30-60 sec] – [Safety Note]
[Stretch Name] – [Target Area] – [Duration: 30-60 sec] – [Safety Note]
[Stretch Name] – [Target Area] – [Duration: 30-60 sec] – [Safety Note]
{"[Stretch Name] – [Target Area] – [Duration: 30-60 sec] – [Safety Note]" if timing['cooldown_exercises'] >= 4 else ""}
"""
        
        prompt_parts.append(structure_section)
        
        # ==================== SECTION 8: QUALITY CHECKLIST ====================
        quality_section = f"""

**8. PRE-SUBMISSION QUALITY CHECKLIST (VERIFY EVERY ITEM):**

**Structural Completeness (100% Required):**
- [ ] Day title: ### {day_name} – {workout_category}
- [ ] Warm-up: {timing['warmup_exercises']} movements, {timing['warmup']} minutes total
- [ ] Main workout: {timing['main_exercises']} exercises, {timing['main']} minutes total
- [ ] Cool-down: {timing['cooldown_exercises']} movements, {timing['cooldown']} minutes total

**Safety Verification (100% Required):**
- [ ] Zero contraindicated exercises for: {', '.join(medical_conditions)}
- [ ] All exercises appropriate for age {age}
- [ ] Intensity respects demographic adjustments ({adjustments['intensity_modifier']:.2f}x modifier)
- [ ] Equipment matches available list only

**Goal Alignment (Must Meet):**
- [ ] Exercises directly support {primary_goal}
- [ ] Rep ranges match: {goal_guidelines.get('rep_range', '10-15')}
- [ ] RPE targets: {goal_guidelines.get('rpe_range', '5-7')}
- [ ] Rest periods: {goal_guidelines.get('rest', '45-60 seconds')}

**Fitness Level Compliance (100% Required):**
- [ ] All exercises match Level {level_num} complexity
- [ ] No exercises above user's level included
- [ ] Modifications provided where needed

**Variety (Must Meet):**
- [ ] Zero repetition from exercises used this week
- [ ] Unique warm-up movements
- [ ] Unique main exercises
- [ ] Unique cool-down stretches

**ACSM Guidelines Adherence:**
- [ ] Follows evidence-based exercise science
- [ ] Appropriate progression and periodization
- [ ] Balanced muscle group targeting
- [ ] Proper work-to-rest ratios
"""
        
        prompt_parts.append(quality_section)
        
        # ==================== SECTION 9: FINAL TASK DIRECTIVE ====================
        if is_modification:
            task = f"""

**YOUR TASK:** Generate a MODIFIED workout plan for {day_name} based on this request: "{modification_request}"

Maintain all safety protocols, goal alignment, and quality standards while incorporating the requested changes.
"""
            if original_plan_context:
                task += f"\n**Original Plan for Reference:**\n{original_plan_context}\n"
        else:
            task = f"""

**YOUR TASK:** Generate a COMPLETE, HIGH-QUALITY workout plan for {day_name} focusing on {workout_category}.

**Remember:**
- Safety is ABSOLUTE priority (zero contraindications)
- Follow ACSM guidelines strictly
- Match exercises to Level {level_num} complexity
- Support {primary_goal} with every exercise choice
- Use only available equipment
- Ensure complete uniqueness from previous days
- Include all required fields for every exercise

**START GENERATING THE WORKOUT PLAN NOW.**
"""
        
        prompt_parts.append(task)
        
        return "\n".join(prompt_parts)
    
    def _get_detailed_condition_guidelines(self, medical_conditions: List[str]) -> str:
        """Get detailed guidelines for each medical condition"""
        guidelines = []
        
        for condition in medical_conditions:
            if condition in CONDITION_GUIDELINES_DB:
                cond_data = CONDITION_GUIDELINES_DB[condition]
                guidelines.append(f"""
**{condition}:**
- ✗ CONTRAINDICATED: {cond_data['contraindicated']}
- ✓ MODIFIED/SAFER: {cond_data['modified']}
- INTENSITY LIMIT: {cond_data['intensity']}
- NOTES: {cond_data['notes']}
""")
            elif condition != "None":
                guidelines.append(f"""
**{condition}:**
- Use conservative approach
- Consult medical database for specific contraindications
- Prioritize low-impact, controlled movements
- Monitor for adverse symptoms
""")
        
        return "\n".join(guidelines) if guidelines else "No specific medical conditions requiring modifications."
    
    def _get_fitness_level_exercise_rules(self, fitness_level: str, level_num: int) -> str:
        """Get detailed exercise selection rules for fitness level"""
        
        level_definitions = {
            1: {
                "name": "Level 1 – Assisted / Low Function",
                "definition": "Needs support for balance; limited endurance; sedentary >6 months",
                "rules": """
**MUST USE:** Supported or assisted exercises only
- Chair-based exercises (chair squats, seated marches, chair push-ups)
- Wall-supported movements (wall push-ups, wall slides)
- Step taps (NO step-ups - too advanced)
- Seated exercises preferred

**STRICTLY PROHIBITED:**
- Floor exercises (getting up/down too difficult)
- Planks, burpees, mountain climbers
- Any jumping or plyometrics
- Floor push-ups (use wall/elevated)
- Lunges (use chair squats)
- Free-standing balance without support

**Example Substitutions:**
- Standard Squat → Chair Sit-to-Stand (assisted)
- Push-up → Wall Push-up
- Lunge → Supported Standing Leg Lift
- Plank → Wall Plank
"""
            },
            2: {
                "name": "Level 2 – Beginner Functional",
                "definition": "Can perform light bodyweight tasks; mild conditions under control",
                "rules": """
**USE:** Low-impact, bodyweight functional exercises with slow tempo
- Partial range bodyweight squats
- Wall/incline push-ups (NOT floor yet)
- Glute bridges (floor work OK at this level)
- Light resistance bands

**STILL PROHIBITED:**
- Floor push-ups (use incline)
- Lunges (use supported step-ups instead)
- Planks >20 seconds
- Jumping, burpees, mountain climbers

**Example Progressions:**
- Wall Push-up → Elevated Push-up (hands on chair)
- Chair Squat → Partial Bodyweight Squat
- Supported Step-up → Low Box Step-up (4-6 inches)
"""
            },
            3: {
                "name": "Level 3 – Moderate / Independent",
                "definition": "Can perform unassisted movements with mild fatigue",
                "rules": """
**USE:** Moderate functional and resistance exercises
- Full bodyweight squats, controlled lunges
- Floor push-ups (can modify to knees)
- Planks (30-60 seconds)
- Light dumbbells (2-10 lbs / 1-5 kg)
- Low-impact cardio

**STILL PROHIBITED:**
- High-impact jumping (jump squats, burpees, box jumps)
- Heavy weights
- Complex Olympic lifts
- Plyometric exercises

**Example Exercises:**
- Bodyweight Squats, Lunges
- Push-ups (full or modified)
- Plank Holds
- Light Dumbbell Rows, Presses
- Glute Bridges, Bird Dogs
"""
            },
            4: {
                "name": "Level 4 – Active Wellness",
                "definition": "No severe limitations; accustomed to regular activity",
                "rules": """
**USE:** Full range of movements, moderate weights
- All bodyweight exercises
- Moderate weight training (10-25 lbs / 5-12 kg)
- Controlled plyometrics (low box jumps, jump squats)
- Compound movements with good form
- Light to moderate intensity intervals

**NOW ALLOWED:**
- Jump squats, box jumps (controlled)
- Burpees (modified or full)
- Mountain climbers
- Moderate weight resistance exercises
- Complex movement patterns

**Example Exercises:**
- Jump Squats, Box Jumps (12-18 inches)
- Full Burpees
- Dumbbell Compound Lifts (rows, presses, deadlifts)
- Advanced Planks (plank to downward dog, plank jacks)
- Kettlebell Swings (light to moderate)
"""
            },
            5: {
                "name": "Level 5 — Advanced / Athletic",
                "definition": "High work capacity; experienced with resistance training; athletic performance",
                "rules": """
**USE:** Full spectrum of exercises including advanced techniques
- Heavy resistance training (>25 lbs / >12 kg)
- Advanced plyometrics (depth jumps, broad jumps)
- Olympic lift variations (cleans, snatches)
- High-intensity intervals (sprints, HIIT)
- Complex movement patterns
- Advanced calisthenics (muscle-ups, pistol squats)

**ALL MOVEMENTS ALLOWED:**
- Maximum intensity plyometrics
- Heavy compound lifts
- Advanced bodyweight progressions
- Sport-specific drills
- Complex multi-joint movements

**Example Exercises:**
- Barbell Squats, Deadlifts (heavy)
- Olympic Lifts (cleans, snatches, jerks)
- Box Jumps (>24 inches), Depth Jumps
- Advanced Calisthenics (pistol squats, one-arm push-ups)
- Full Burpees with Jump
- Kettlebell Swings (heavy), Turkish Get-ups
- Sprint Intervals
"""
            }
        }
        
        if level_num in level_definitions:
            level_info = level_definitions[level_num]
            return f"""
**{level_info['name']}**
**Definition:** {level_info['definition']}

{level_info['rules']}
"""
        
        return "Use exercises appropriate for intermediate fitness level."
    
    def _get_location_equipment_exercises(self, location: str, available_equipment: List[str], workout_category: str) -> str:
        """Get location and equipment-appropriate exercise examples"""
        
        equipment_str = ', '.join(available_equipment).lower()
        
        exercises = {
            "bodyweight_only": """
**Bodyweight-Only Exercises:**
- Lower Body: Squats, Lunges, Step-ups, Glute Bridges, Calf Raises, Wall Sits
- Upper Body: Push-ups (standard/modified/decline), Pike Push-ups, Tricep Dips (chair)
- Core: Planks, Side Planks, Bird Dogs, Dead Bugs, Bicycle Crunches, Leg Raises
- Cardio: High Knees, Butt Kicks, Jumping Jacks, Mountain Climbers, Burpees
- Balance: Single-leg Stands, Balance Reaches, Heel-to-Toe Walk
""",
            "dumbbells": """
**Dumbbell Exercises:**
- Lower Body: Goblet Squats, Dumbbell Lunges, Romanian Deadlifts, Step-ups with Dumbbells
- Upper Body: Chest Press, Shoulder Press, Bent-over Rows, Bicep Curls, Tricep Extensions
- Core: Weighted Russian Twists, Dumbbell Side Bends, Renegade Rows
- Full Body: Dumbbell Thrusters, Man Makers
""",
            "resistance_bands": """
**Resistance Band Exercises:**
- Lower Body: Banded Squats, Lateral Band Walks, Banded Glute Bridges, Leg Press (anchored)
- Upper Body: Banded Chest Press, Rows, Shoulder Raises, Bicep Curls, Tricep Extensions
- Core: Pallof Press, Banded Wood Chops, Anti-rotation Hold
- Mobility: Band-assisted Stretches, Shoulder Dislocations
""",
            "kettlebells": """
**Kettlebell Exercises:**
- Full Body: Kettlebell Swings, Turkish Get-ups, Goblet Squats
- Upper Body: Kettlebell Press, Rows, Halos
- Lower Body: Single-leg Deadlifts, Lunges
- Core: Windmills, Around-the-World
""",
            "yoga_mat": """
**Mat-Based Exercises:**
- Core: All plank variations, abdominal work, leg raises
- Flexibility: Yoga poses, stretching routines
- Bodyweight: Floor push-ups, glute bridges, leg raises
""",
            "pull_up_bar": """
**Pull-up Bar Exercises:**
- Upper Body: Pull-ups, Chin-ups, Hanging Knee Raises, Hanging Leg Raises
- Core: Hanging Oblique Raises, L-sits
- Modifications: Assisted variations, negative reps, dead hangs
""",
            "bench": """
**Bench/Chair Exercises:**
- Upper Body: Bench Press, Incline/Decline variations, Tricep Dips
- Lower Body: Step-ups, Bulgarian Split Squats, Box Jumps
- Support: Assisted exercises, elevated push-ups
""",
            "home_items": """
**Household Item Alternatives:**
- Chair: Tricep dips, step-ups, support for squats, elevated push-ups
- Wall: Wall push-ups, wall sits, wall slides, balance support
- Towel: Slider exercises (towel slides), resistance (towel rows)
- Water Bottles: Light dumbbell substitute (2-4 lbs each)
- Backpack: Weighted vest alternative (fill with books)
- Stairs: Step-ups, calf raises, incline push-ups
"""
        }
        
        result = []
        
        # Check for equipment types
        if 'bodyweight' in equipment_str or 'none' in equipment_str:
            result.append(exercises['bodyweight_only'])
        
        if 'dumbbell' in equipment_str:
            result.append(exercises['dumbbells'])
        
        if 'resistance band' in equipment_str or 'band' in equipment_str:
            result.append(exercises['resistance_bands'])
        
        if 'kettlebell' in equipment_str:
            result.append(exercises['kettlebells'])
        
        if 'yoga mat' in equipment_str or 'mat' in equipment_str:
            result.append(exercises['yoga_mat'])
        
        if 'pull-up bar' in equipment_str or 'pull up' in equipment_str:
            result.append(exercises['pull_up_bar'])
        
        if 'bench' in equipment_str or 'chair' in equipment_str:
            result.append(exercises['bench'])
        
        # Always include household items for home workouts
        if location.lower() == 'home':
            result.append(exercises['home_items'])
        
        if not result:
            result.append(exercises['bodyweight_only'])
        
        return "\n".join(result)
    
    def _format_used_exercises(self) -> str:
        """Format the list of exercises already used this week"""
        if not any(self.weekly_exercises_used.values()):
            return "None yet - this is the first day or a fresh week."
        
        formatted = []
        
        if self.weekly_exercises_used['warmup']:
            formatted.append(f"**Warm-up:** {', '.join(sorted(self.weekly_exercises_used['warmup']))}")
        
        if self.weekly_exercises_used['main']:
            formatted.append(f"**Main Workout:** {', '.join(sorted(self.weekly_exercises_used['main']))}")
        
        if self.weekly_exercises_used['cooldown']:
            formatted.append(f"**Cool-down:** {', '.join(sorted(self.weekly_exercises_used['cooldown']))}")
        
        return "\n".join(formatted) if formatted else "None yet - this is the first day or a fresh week."
    
    def _get_warmup_examples(self, fitness_level: str, goal: str) -> str:
        """Get warm-up examples based on fitness level and goal"""
        # Preserved from original - add implementation if needed
        return "Dynamic movements, joint mobility, light cardio preparation"
    
    def _get_cooldown_examples(self, fitness_level: str, goal: str) -> str:
        """Get cool-down examples based on fitness level and goal"""
        # Preserved from original - add implementation if needed
        return "Static stretches, breathing exercises, gentle mobility work"
    
    def _get_exercise_selection_guidance(self, goal: str, category: str) -> str:
        """Get exercise selection guidance for specific goals and categories"""
        # Preserved from original - add implementation if needed
        return f"Select exercises that align with {goal} and focus on {category}"
    
    def _get_equipment_appropriate_exercises(self, equipment: List[str], category: str) -> str:
        """Get exercises appropriate for available equipment"""
        # Preserved from original - add implementation if needed
        return self._get_location_equipment_exercises("", equipment, category)
    
    def _get_precise_intensity_rules(self, goal: str, level: str) -> str:
        """Get precise intensity rules based on goal and level"""
        # Preserved from original - add implementation if needed
        goal_guidelines = self.goal_programming_guidelines.get(goal, self.goal_programming_guidelines["General Fitness"])
        return f"RPE: {goal_guidelines.get('rpe_range', '5-7')}, Rest: {goal_guidelines.get('rest', '45-60 seconds')}"
    
    def _get_condition_guidelines(self, conditions: List[str]) -> str:
        """Get condition-specific guidelines"""
        # Preserved from original - add implementation if needed
        return self._get_detailed_condition_guidelines(conditions)
    
    def _get_age_adaptations(self, age: int) -> str:
        """Get age-specific adaptations"""
        # Preserved from original - add implementation if needed
        if age >= 60:
            return "Reduced intensity, extended warm-up, joint-friendly movements, balance focus"
        elif age >= 40:
            return "Moderate intensity, proper warm-up, recovery emphasis"
        else:
            return "Standard progression, age-appropriate intensity"
    
    def _determine_exercise_count(self, duration: str, section: str) -> int:
        """Determine exercise count based on duration and section"""
        timing = self._calculate_session_timing(duration)
        if section == "warmup":
            return timing['warmup_exercises']
        elif section == "main":
            return timing['main_exercises']
        elif section == "cooldown":
            return timing['cooldown_exercises']
        return 5
    
    def generate_workout_plan(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        workout_category: str = "Full Body"
    ) -> Dict:
        """
        Generate a single day's workout plan
        
        Returns:
            Dict with 'success', 'plan', 'exercises_used', 'error' keys
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(
                user_profile=user_profile,
                day_name=day_name,
                day_index=day_index,
                workout_category=workout_category
            )
            
            # Make API call
            response = requests.post(
                self.endpoint_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4000,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Generate the complete workout plan for {day_name} now."
                        }
                    ]
                },
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract plan text
            plan_text = ""
            if "content" in result and isinstance(result["content"], list):
                for block in result["content"]:
                    if block.get("type") == "text":
                        plan_text += block.get("text", "")
            
            if not plan_text:
                raise ValueError("Empty response from API")
            
            # Extract exercises used
            exercises_used = self._extract_exercises_from_plan(plan_text)
            
            # Validate plan
            validation = self._validate_plan(plan_text, user_profile, day_name)
            
            return {
                "success": True,
                "plan": plan_text,
                "exercises_used": exercises_used,
                "validation": validation,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "plan": self._generate_fallback_plan(user_profile, day_name, workout_category),
                "exercises_used": {},
                "validation": {"valid": False, "issues": [str(e)]},
                "error": str(e)
            }
    
    def _extract_exercises_from_plan(self, plan_text: str) -> Dict:
        """Extract exercise names from generated plan"""
        exercises = {
            'warmup': [],
            'main': [],
            'cooldown': []
        }
        
        current_section = None
        lines = plan_text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect sections
            if 'warm-up' in line_lower or 'warm up' in line_lower:
                current_section = 'warmup'
            elif 'main workout' in line_lower or 'main circuit' in line_lower:
                current_section = 'main'
            elif 'cool-down' in line_lower or 'cool down' in line_lower or 'cooldown' in line_lower:
                current_section = 'cooldown'
            
            # Extract exercise names (lines starting with numbers or bullets)
            if current_section and (line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '-', '•', '*'))):
                # Clean up the exercise name
                exercise_name = line.strip()
                for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '-', '•', '*', '**']:
                    exercise_name = exercise_name.lstrip(prefix).strip()
                
                # Remove markdown formatting
                exercise_name = exercise_name.split('—')[0].split('–')[0].split(':')[0].strip()
                exercise_name = exercise_name.replace('**', '').strip()
                
                if exercise_name and len(exercise_name) > 3:
                    exercises[current_section].append(exercise_name)
        
        return exercises
    
    def _validate_plan(self, plan_text: str, user_profile: Dict, day_name: str) -> Dict:
        """Validate the generated workout plan"""
        issues = []
        
        # Check for required sections
        if 'warm-up' not in plan_text.lower() and 'warm up' not in plan_text.lower():
            issues.append("Missing warm-up section")
        
        if 'main workout' not in plan_text.lower() and 'main circuit' not in plan_text.lower():
            issues.append("Missing main workout section")
        
        if 'cool-down' not in plan_text.lower() and 'cool down' not in plan_text.lower() and 'cooldown' not in plan_text.lower():
            issues.append("Missing cool-down section")
        
        # Check for day title
        if day_name not in plan_text:
            issues.append(f"Missing day title: {day_name}")
        
        # Check minimum length
        if len(plan_text) < 500:
            issues.append("Plan appears too short")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _generate_fallback_plan(self, user_profile: Dict, day_name: str, workout_category: str) -> str:
        """Generate a simple fallback plan if API fails"""
        timing = self._calculate_session_timing(user_profile.get("session_duration", "30-45 minutes"))
        
        return f"""### {day_name} — {workout_category}

**Warm-Up ({timing['warmup']} minutes)**

1. March in Place — Cardiovascular preparation — 2 minutes — Maintain upright posture
2. Arm Circles — Shoulder mobility — 30 seconds each direction — Controlled movement
3. Leg Swings — Hip mobility — 10 per leg — Use wall for support if needed

**Main Workout ({timing['main']} minutes)**

1. Bodyweight Squats
   - Sets × Reps: 3 × 12
   - Rest: 60 seconds
   - Focus on form and controlled movement

2. Push-ups (Modified if needed)
   - Sets × Reps: 3 × 10
   - Rest: 60 seconds
   - Keep core engaged

3. Glute Bridges
   - Sets × Reps: 3 × 15
   - Rest: 45 seconds
   - Squeeze glutes at top

4. Plank Hold
   - Duration: 3 × 30 seconds
   - Rest: 45 seconds
   - Maintain neutral spine

**Cool-Down ({timing['cooldown']} minutes)**

1. Hamstring Stretch — 60 seconds per leg
2. Quad Stretch — 60 seconds per leg
3. Child's Pose — 60 seconds

*Note: This is a fallback plan. Please retry for a personalized workout.*
"""
    
    def generate_full_program(self, user_profile: Dict) -> Dict:
        """
        Generate complete weekly workout program
        
        Returns:
            Dict with 'success', 'weekly_plans', 'summary', 'error' keys
        """
        self.reset_weekly_tracker()
        
        days_per_week = user_profile.get("days_per_week", [])
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        fitness_level = user_profile.get("fitness_level", "Level 3 - Intermediate")
        
        # Determine workout categories for each day
        distribution = self._determine_workout_distribution(len(days_per_week), fitness_level, primary_goal)
        categories = distribution.get('split_categories', ['Full Body'] * len(days_per_week))
        
        weekly_plans = []
        all_exercises = {'warmup': [], 'main': [], 'cooldown': []}
        
        for idx, day_name in enumerate(days_per_week):
            workout_category = categories[idx] if idx < len(categories) else "Full Body"
            
            # Generate plan for this day
            result = self.generate_workout_plan(
                user_profile=user_profile,
                day_name=day_name,
                day_index=idx,
                workout_category=workout_category
            )
            
            # Track exercises used
            if result['success'] and result['exercises_used']:
                for section, exercises in result['exercises_used'].items():
                    self.weekly_exercises_used[section].update(exercises)
                    all_exercises[section].extend(exercises)
            
            weekly_plans.append({
                "day": day_name,
                "category": workout_category,
                "plan": result['plan'],
                "success": result['success'],
                "validation": result.get('validation', {}),
                "error": result.get('error')
            })
        
        # Generate program summary
        summary = self._generate_program_summary(user_profile, weekly_plans, all_exercises)
        
        return {
            "success": all(plan['success'] for plan in weekly_plans),
            "weekly_plans": weekly_plans,
            "summary": summary,
            "total_days": len(days_per_week),
            "exercises_used": all_exercises
        }
    
    def _generate_program_summary(self, user_profile: Dict, weekly_plans: List[Dict], all_exercises: Dict) -> str:
        """Generate a summary of the weekly program"""
        name = user_profile.get("name", "User")
        goal = user_profile.get("primary_goal", "General Fitness")
        days = len(weekly_plans)
        
        summary = f"""# Weekly Fitness Program Summary for {name}

**Primary Goal:** {goal}
**Training Frequency:** {days} days per week
**Total Unique Exercises:** {len(set(all_exercises['main']))}

## Weekly Structure:
"""
        
        for plan in weekly_plans:
            status = "✓" if plan['success'] else "✗"
            summary += f"\n{status} **{plan['day']}** — {plan['category']}"
        
        summary += f"""

## Exercise Variety:
- Warm-up movements: {len(set(all_exercises['warmup']))} unique
- Main exercises: {len(set(all_exercises['main']))} unique
- Cool-down stretches: {len(set(all_exercises['cooldown']))} unique

## Safety & Personalization:
- All exercises matched to fitness level
- Medical conditions accommodated
- Equipment limitations respected
- Progressive overload applied throughout week
"""
        
        return summary
    
    def modify_workout_plan(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        modification_request: str,
        original_plan: str,
        workout_category: str = "Full Body"
    ) -> Dict:
        """
        Modify an existing workout plan based on user request
        """
        try:
            system_prompt = self._build_system_prompt(
                user_profile=user_profile,
                day_name=day_name,
                day_index=day_index,
                workout_category=workout_category,
                is_modification=True,
                modification_request=modification_request,
                original_plan_context=original_plan[:1000]  # First 1000 chars for context
            )
            
            response = requests.post(
                self.endpoint_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4000,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Generate the modified workout plan for {day_name} based on the request: {modification_request}"
                        }
                    ]
                },
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            plan_text = ""
            if "content" in result and isinstance(result["content"], list):
                for block in result["content"]:
                    if block.get("type") == "text":
                        plan_text += block.get("text", "")
            
            exercises_used = self._extract_exercises_from_plan(plan_text)
            
            return {
                "success": True,
                "plan": plan_text,
                "exercises_used": exercises_used,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "plan": original_plan,
                "exercises_used": {},
                "error": str(e)
            }
    
    def get_exercise_library(self, fitness_level: str, equipment: List[str]) -> Dict:
        """Get categorized exercise library based on fitness level and equipment"""
        level_num = self._extract_level_number(fitness_level)
        
        library = {
            "lower_body": [],
            "upper_body": [],
            "core": [],
            "cardio": [],
            "flexibility": []
        }
        
        # This would be populated with actual exercise data
        # For now, returning structure
        return library
    
    def export_program_to_markdown(self, program_data: Dict, user_profile: Dict) -> str:
        """Export full program to markdown format"""
        markdown = f"""# Personalized Fitness Program
## Generated by FriskaAI

**Client:** {user_profile.get('name', 'User')}
**Goal:** {user_profile.get('primary_goal', 'General Fitness')}
**Fitness Level:** {user_profile.get('fitness_level', 'Intermediate')}
**Program Duration:** Weekly
**Generated:** {datetime.now().strftime('%Y-%m-%d')}

---

"""
        
        for plan in program_data.get('weekly_plans', []):
            markdown += f"\n{plan['plan']}\n\n---\n"
        
        markdown += f"\n\n{program_data.get('summary', '')}"
        
        return markdown
    
    def get_weekly_variety_report(self) -> Dict:
        """Get report on exercise variety across the week"""
        return {
            "warmup_unique": len(self.weekly_exercises_used['warmup']),
            "main_unique": len(self.weekly_exercises_used['main']),
            "cooldown_unique": len(self.weekly_exercises_used['cooldown']),
            "warmup_exercises": list(self.weekly_exercises_used['warmup']),
            "main_exercises": list(self.weekly_exercises_used['main']),
            "cooldown_exercises": list(self.weekly_exercises_used['cooldown'])
        }


# Condition Guidelines Database (referenced in the class)
CONDITION_GUIDELINES_DB = {
    "Hypertension": {
        "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing with heavy loads",
        "modified": "Moderate resistance with higher reps, controlled breathing, avoid breath-holding",
        "intensity": "RPE 5-7, avoid RPE >8",
        "notes": "Monitor during exercise, rest adequately between sets"
    },
    "Type 2 Diabetes": {
        "contraindicated": "Extreme intensity without proper monitoring",
        "modified": "Moderate cardio + resistance, monitor blood glucose",
        "intensity": "RPE 5-7",
        "notes": "Exercise at consistent times, have fast-acting carbs available"
    },
    "Osteoarthritis": {
        "contraindicated": "High-impact jumping, deep knee bends with load, exercises causing pain",
        "modified": "Low-impact cardio, controlled ROM, joint-friendly resistance",
        "intensity": "RPE 4-6",
        "notes": "Avoid exercises that cause joint pain, emphasize mobility"
    },
    "Lower Back Pain": {
        "contraindicated": "Heavy spinal loading, deep forward flexion, ballistic twisting",
        "modified": "Core stability, neutral spine exercises, pain-free ROM",
        "intensity": "RPE 3-6",
        "notes": "Focus on core stability, avoid end-range spinal movements"
    },
    "Obesity": {
        "contraindicated": "High-impact jumping, exercises requiring full body weight support",
        "modified": "Low-impact cardio, seated exercises, gradual progression",
        "intensity": "RPE 4-7",
        "notes": "Prioritize joint protection, gradual intensity increase"
    },
    "Cardiovascular Disease": {
        "contraindicated": "Maximal intensity, Valsalva, extreme isometric holds",
        "modified": "Moderate continuous or interval cardio, controlled resistance",
        "intensity": "RPE 4-6, medical clearance required",
        "notes": "Medical supervision recommended, avoid extreme intensity"
    },
    "Asthma": {
        "contraindicated": "Prolonged high-intensity without breaks",
        "modified": "Interval training, extended warm-up, inhaler accessible",
        "intensity": "RPE 5-7",
        "notes": "Have rescue inhaler available, avoid cold/dry air if triggers"
    }
}

# ============ CUSTOM CSS ============
def inject_custom_css():
    """Inject modern, professional CSS styling"""
    st.markdown("""
    <style>
    /* Main App Styling */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    /* Header Styling */
    .header-container {
        background: Black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .header-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .header-subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    
    /* Form Sections */
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1.5rem 0 1rem 0;
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    /* Info Boxes */
    .info-box {
        background: black;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: Black;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: black;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* BMI Result Styling */
    .bmi-container {
        background: Black;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    .bmi-value {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .bmi-category {
        font-size: 1.2rem;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Workout Plan Styling */
    .workout-day {
        background: black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1.5rem 0;
    }
    
    /* Footer Styling */
    .footer {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-top: 3rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 5px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# ============ SESSION STATE INITIALIZATION ============
def initialize_session_state():
    """Initialize all session state variables"""
    if 'fitness_plan_generated' not in st.session_state:
        st.session_state.fitness_plan_generated = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {}
    if 'workout_plans' not in st.session_state:
        st.session_state.workout_plans = {}
    if 'feedback_submitted' not in st.session_state:
        st.session_state.feedback_submitted = False

# ============ MAIN APPLICATION ============
def main():
    """Main application function"""
    
    # Initialize
    inject_custom_css()
    initialize_session_state()
    advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)
    
    # ============ HEADER ============
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">💪 FriskaAI Fitness Coach</h1>
        <p class="header-subtitle">Your Personalized, Medically-Safe AI Fitness Partner</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============ MAIN FORM ============
    if not st.session_state.fitness_plan_generated:
        
        st.markdown('<div class="info-box">📋 <strong>Complete the form below to receive your personalized fitness plan.</strong> All information is kept confidential and used only to create your safe, effective workout program.</div>', unsafe_allow_html=True)
        
        with st.form("fitness_assessment_form"):
            
            # ===== SECTION 1: BASIC INFORMATION =====
            st.markdown('<div class="section-header">📝 Section 1: Basic Information</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *", placeholder="Enter your name")
                age = st.number_input("Age *", min_value=13, max_value=100, value=30, step=1)
                gender = st.selectbox("Gender *", ["Male", "Female", "Other", "Prefer not to say"])
            
            with col2:
    # Unit selection
                unit_system = st.radio("Measurement System *", ["Metric (kg, cm)", "Imperial (lbs, inches)"], horizontal=True)
                
                if unit_system == "Metric (kg, cm)":
                    weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=70.0, step=0.5)
                    height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
                else:  # Imperial
                    weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=154.0, step=1.0)
                    height_inches = st.number_input("Height (inches) *", min_value=39.0, max_value=98.0, value=67.0, step=0.5)
                    
                    # Convert to metric for internal use
                    weight_kg = weight_lbs * 0.453592
                    height_cm = height_inches * 2.54
            # BMI Calculation
            if weight_kg > 0 and height_cm > 0:
                bmi = weight_kg / ((height_cm / 100) ** 2)
                
                if bmi < 18.5:
                    bmi_category = "Underweight"
                    bmi_color = "#ff9800"
                elif 18.5 <= bmi < 25:
                    bmi_category = "Normal Weight"
                    bmi_color = "#4caf50"
                elif 25 <= bmi < 30:
                    bmi_category = "Overweight"
                    bmi_color = "#ff9800"
                else:
                    bmi_category = "Obese"
                    bmi_color = "#f44336"
                
                st.markdown(f"""
                <div class="bmi-container">
                    <div style="color: #666;">Your BMI</div>
                    <div class="bmi-value" style="color: {bmi_color};">{bmi:.1f}</div>
                    <div class="bmi-category" style="color: {bmi_color};">{bmi_category}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # ===== SECTION 2: GOALS & FITNESS LEVEL =====
            st.markdown('<div class="section-header">🎯 Section 2: Goals & Fitness Level</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                primary_goal = st.selectbox(
                    "Primary Fitness Goal *",
                    [
                        "Weight Loss",
                        "Muscle Gain",
                        "Increase Overall Strength",
                        "Improve Cardiovascular Fitness",
                        "Improve Flexibility & Mobility",
                        "Rehabilitation & Injury Prevention",
                        "Improve Posture and Balance",
                        "General Fitness"
                    ]
                )
            
            with col2:
                fitness_level = st.selectbox(
                    "Current Fitness Level *",
                    [
                        "Level 1 – Assisted / Low Function",
                        "Level 2 – Beginner Functional",
                        "Level 3 – Moderate / Independent  ",
                        "Level 4 – Active Wellness  ",
                        "Level 5 – Adaptive Advanced"
                    ]
                )
            
            # ===== SECTION 3: HEALTH SCREENING =====
            st.markdown('<div class="section-header">🏥 Section 3: Health Screening (Critical for Safety)</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="warning-box">⚠️ <strong>Medical Conditions:</strong> Selecting your conditions helps us create a SAFE workout plan. All exercises will be adapted to avoid contraindicated movements.</div>', unsafe_allow_html=True)
            
            medical_conditions = st.multiselect(
                "Do you have any of these medical conditions? (Select all that apply) *",
                MEDICAL_CONDITIONS,
                default=["None"]
            )
            
            # Remove "None" if other conditions are selected
            if len(medical_conditions) > 1 and "None" in medical_conditions:
                medical_conditions = [c for c in medical_conditions if c != "None"]
            
            physical_limitations = st.text_area(
                "Physical Limitations or Injuries",
                placeholder="E.g., previous knee surgery, shoulder pain, limited mobility in right hip...",
                help="Describe any injuries, pain, or movement restrictions"
            )
            
            current_medications = st.text_area(
                "Current Medications (Optional)",
                placeholder="E.g., blood pressure medication, insulin, beta-blockers...",
                help="Some medications affect exercise response"
            )
            
            # Medical Clearance Check
            if age >= 65 or any(cond not in ["None", "Other"] for cond in medical_conditions):
                st.markdown('<div class="warning-box">⚠️ <strong>Medical Clearance Recommended:</strong> Based on your profile, we recommend consulting a physician before starting a new exercise program. Our plans are designed to be safe, but medical supervision is advised.</div>', unsafe_allow_html=True)
            
            # ===== SECTION 4: WORKOUT PREFERENCES =====
            st.markdown('<div class="section-header">💪 Section 4: Workout Preferences</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                workout_location = st.selectbox(
                    "Where will you work out? *",
                    ["Home", "Gym", "Outdoor/Park", "Office", "Mixed Locations"]
                )
                
                session_duration = st.selectbox(
                    "Session Duration *",
                    ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes", "60+ minutes"]
                )
            
            with col2:
                days_per_week = st.multiselect(
                    "Select Training Days *",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    default=["Monday", "Wednesday", "Friday"]
                )
                
                workout_time = st.selectbox(
                    "Preferred Workout Time",
                    ["Early Morning (5-8 AM)", "Morning (8-12 PM)", "Afternoon (12-5 PM)", "Evening (5-8 PM)", "Night (8 PM+)", "Flexible"]
                )
            
            # Equipment Selection
            st.markdown("**Available Equipment** (Select all that apply) *")
            
            equipment_cols = st.columns(3)
            
            with equipment_cols[0]:
                eq_bodyweight = st.checkbox("None - Bodyweight Only", value=True)
                eq_dumbbells = st.checkbox("Dumbbells")
                eq_resistance_bands = st.checkbox("Resistance Bands")
                eq_kettlebells = st.checkbox("Kettlebells")
            
            with equipment_cols[1]:
                eq_barbell = st.checkbox("Barbell & Plates")
                eq_bench = st.checkbox("Bench")
                eq_pullup_bar = st.checkbox("Pull-up Bar")
                eq_yoga_mat = st.checkbox("Yoga Mat")
            
            with equipment_cols[2]:
                eq_cardio = st.checkbox("Cardio Machine (Treadmill/Bike)")
                eq_trx = st.checkbox("TRX/Suspension Trainer")
                eq_medicine_ball = st.checkbox("Medicine Ball")
                eq_foam_roller = st.checkbox("Foam Roller")
            
            # Compile equipment list
            available_equipment = []
            if eq_bodyweight: available_equipment.append("None - Bodyweight Only")
            if eq_dumbbells: available_equipment.append("Dumbbells")
            if eq_resistance_bands: available_equipment.append("Resistance Bands")
            if eq_kettlebells: available_equipment.append("Kettlebells")
            if eq_barbell: available_equipment.append("Barbell & Plates")
            if eq_bench: available_equipment.append("Bench")
            if eq_pullup_bar: available_equipment.append("Pull-up Bar")
            if eq_yoga_mat: available_equipment.append("Yoga Mat")
            if eq_cardio: available_equipment.append("Cardio Machine")
            if eq_trx: available_equipment.append("TRX/Suspension Trainer")
            if eq_medicine_ball: available_equipment.append("Medicine Ball")
            if eq_foam_roller: available_equipment.append("Foam Roller")
            
            if not available_equipment:
                available_equipment = ["None - Bodyweight Only"]
            
            # Target Areas
            target_areas = st.multiselect(
                "Target Areas / Focus *",
                [
                    "Full Body",
                    "Upper Body (Chest, Back, Arms)",
                    "Lower Body (Legs, Glutes)",
                    "Core & Abs",
                    "Back & Posture",
                    "Arms & Shoulders",
                    "Legs & Glutes",
                    "Cardiovascular System",
                    "Flexibility & Mobility"
                ],
                default=["Full Body"]
            )
            
            # ===== FORM SUBMISSION =====
            st.markdown("---")
            submit_button = st.form_submit_button("🚀 Generate My Personalized Fitness Plan", use_container_width=True)
            
            if submit_button:
                # Validation
                validation_errors = []
                
                if not name or len(name.strip()) < 2:
                    validation_errors.append("❌ Please enter your full name")
                
                if age < 13:
                    validation_errors.append("❌ You must be at least 13 years old to use this service")
                
                if not days_per_week or len(days_per_week) == 0:
                    validation_errors.append("❌ Please select at least one training day")
                
                if not target_areas or len(target_areas) == 0:
                    validation_errors.append("❌ Please select at least one target area")
                
                # Display validation errors
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # Store user profile
                    st.session_state.user_profile = {
                        "name": name.strip(),
                        "age": age,
                        "gender": gender,
                        "weight_kg": weight_kg,
                        "height_cm": height_cm,
                        "bmi": round(bmi, 1) if weight_kg > 0 and height_cm > 0 else 0,
                        "primary_goal": primary_goal,
                        "fitness_level": fitness_level,
                        "medical_conditions": medical_conditions,
                        "physical_limitations": physical_limitations,
                        "current_medications": current_medications,
                        "workout_location": workout_location,
                        "session_duration": session_duration,
                        "days_per_week": days_per_week,
                        "workout_time": workout_time,
                        "available_equipment": available_equipment,
                        "target_areas": target_areas,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Generate workout plans
                    # Generate workout plans
                    with st.spinner("🔄 Generating your personalized fitness plan... This may take 30-60 seconds."):
                        try:
                            progress_bar = st.progress(0)
                            
                            for idx, day in enumerate(days_per_week):
                                progress = (idx + 1) / len(days_per_week)
                                progress_bar.progress(progress)
                                
                                result = advisor.generate_workout_plan(
                                    st.session_state.user_profile,
                                    day,
                                    idx
                                )
                                
                                # Store the complete result
                                st.session_state.workout_plans[day] = result
                            
                            progress_bar.empty()
                            st.session_state.fitness_plan_generated = True
                            st.success("✅ Your personalized fitness plan is ready!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error generating plan: {str(e)}")
                            st.error("Please try again or contact support if the issue persists.")
    
    # ============ DISPLAY FITNESS PLAN ============
    else:
        profile = st.session_state.user_profile
        
        # Header with user info
        st.markdown(f"""
        <div class="success-box">
            <h2>👋 Welcome, {profile['name']}!</h2>
            <p><strong>Your Personalized Fitness Plan is Ready</strong></p>
            <p>📅 Generated: {profile['timestamp']} | 🎯 Goal: {profile['primary_goal']} | 💪 Level: {profile['fitness_level']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Medical Safety Summary
        if profile['medical_conditions'] and profile['medical_conditions'] != ["None"]:
            st.markdown(f"""
            <div class="warning-box">
                <strong>🏥 Medical Adaptations Applied:</strong><br>
                Your plan has been customized to accommodate: <strong>{', '.join(profile['medical_conditions'])}</strong><br>
                All contraindicated exercises have been removed or modified for your safety.
            </div>
            """, unsafe_allow_html=True)
        
        # Display workout plans
        # Display workout plans
        st.markdown('<div class="section-header">📅 Your Weekly Workout Schedule</div>', unsafe_allow_html=True)

        for day in profile['days_per_week']:
            with st.expander(f"📋 {day} Workout Plan", expanded=False):
                if day in st.session_state.workout_plans:
                    plan_data = st.session_state.workout_plans[day]
                    
                    # Check if it's the result dictionary or just the plan text
                    if isinstance(plan_data, dict):
                        plan_text = plan_data.get('plan', '')
                        validation_score = plan_data.get('validation_score', 0)
                    else:
                        plan_text = plan_data
                    
                    # Display the workout plan with proper markdown rendering
                    st.markdown(plan_text)
                else:
                    st.warning(f"Plan for {day} not available. Please regenerate.")
        
        # Download button
        # Download button
        st.markdown("---")
        full_plan = f"""
# FriskaAI Personalized Fitness Plan
Generated: {profile['timestamp']}

## User Profile
- Name: {profile['name']}
- Age: {profile['age']} | Gender: {profile['gender']}
- BMI: {profile['bmi']} | Weight: {profile['weight_kg']} kg | Height: {profile['height_cm']} cm
- Fitness Level: {profile['fitness_level']}
- Primary Goal: {profile['primary_goal']}
- Medical Conditions: {', '.join(profile['medical_conditions'])}
- Physical Limitations: {profile['physical_limitations'] if profile['physical_limitations'] else 'None'}
- Training Days: {', '.join(profile['days_per_week'])}
- Session Duration: {profile['session_duration']}
- Location: {profile['workout_location']}
- Equipment: {', '.join(profile['available_equipment'])}

## Weekly Workout Schedule

"""

        for day in profile['days_per_week']:
            if day in st.session_state.workout_plans:
                plan_data = st.session_state.workout_plans[day]
                # Extract plan text if it's a dictionary
                if isinstance(plan_data, dict):
                    plan_text = plan_data.get('plan', '')
                else:
                    plan_text = plan_data
                full_plan += f"\n{plan_text}\n\n---\n"

        full_plan += """
## Important Safety Reminders

⚠️ Stop exercising immediately if you experience:
- Chest pain or pressure
- Severe shortness of breath
- Dizziness or lightheadedness
- Unusual fatigue
- Sharp or severe pain

✓ Always warm up before and cool down after workouts
✓ Stay hydrated throughout your session
✓ Listen to your body and adjust intensity as needed
✓ Consult your physician if you have concerns

Generated by FriskaAI - Your AI Fitness Coach
"""
        
        st.download_button(
            label="📥 Download Complete Fitness Plan (Markdown)",
            data=full_plan,
            file_name=f"FriskaAI_Fitness_Plan_{profile['name']}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.fitness_plan_generated = False
                st.session_state.workout_plans = {}
                st.rerun()
        
        with col2:
            if st.button("✏️ Modify Existing Plan", use_container_width=True):
                st.info("💡 To modify your plan, click 'Generate New Plan' and adjust your preferences.")
        
        # ============ FEEDBACK SECTION ============
        st.markdown('<div class="section-header">💬 Feedback & Support</div>', unsafe_allow_html=True)
        
        if not st.session_state.feedback_submitted:
            with st.form("feedback_form"):
                st.markdown("**Help us improve FriskaAI!** Your feedback is valuable.")
                
                rating = st.slider("How satisfied are you with your fitness plan?", 1, 5, 5)
                feedback_text = st.text_area("Comments or suggestions (optional)", placeholder="What did you like? What could be better?")
                
                submit_feedback = st.form_submit_button("Submit Feedback")
                
                if submit_feedback:
                    st.session_state.feedback_submitted = True
                    st.success("✅ Thank you for your feedback! We appreciate your input.")
                    st.balloons()
        else:
            st.markdown('<div class="success-box">✅ Thank you for submitting your feedback!</div>', unsafe_allow_html=True)
    
    # ============ FAQ SECTION ============
    st.markdown("---")
    st.markdown('<div class="section-header">❓ Frequently Asked Questions</div>', unsafe_allow_html=True)
    
    with st.expander("🔍 How is my fitness plan personalized?"):
        st.markdown("""
        FriskaAI uses advanced AI to analyze:
        - Your medical conditions and physical limitations
        - Age, fitness level, and experience
        - Available equipment and workout location
        - Primary fitness goals and target areas
        - Time constraints and scheduling preferences
        
        Every exercise is cross-referenced against medical contraindications to ensure safety.
        """)
    
    with st.expander("🏥 Is this safe if I have medical conditions?"):
        st.markdown("""
        FriskaAI implements strict medical safety protocols:
        - Contraindicated exercises are automatically excluded
        - Intensity is adjusted based on your conditions
        - Modified, safer alternatives are provided
        - Age-appropriate adaptations are applied
        
        **However:** Always consult your physician before starting a new exercise program, especially if you have medical conditions or are over 65.
        """)
    
    with st.expander("📊 What does RPE mean?"):
        st.markdown("""
        **RPE = Rate of Perceived Exertion** (1-10 scale)
        
        - **1-2:** Very Light (minimal effort)
        - **3-4:** Light (can talk easily)
        - **5-6:** Moderate (can talk in short sentences)
        - **7-8:** Hard (difficult to speak)
        - **9-10:** Very Hard to Maximal (cannot maintain)
        
        Use RPE to self-regulate your workout intensity based on how you feel.
        """)
    
    with st.expander("🔄 Can I modify my plan?"):
        st.markdown("""
        Yes! You can:
        - Click "Generate New Plan" to start fresh with different parameters
        - Adjust exercises yourself based on how your body responds
        - Increase or decrease intensity as you progress
        - Substitute exercises if equipment is unavailable
        
        Listen to your body and make adjustments as needed for safety and effectiveness.
        """)
    
    with st.expander("⏱️ How long should I follow this plan?"):
        st.markdown("""
        **Recommended Duration:**
        - Beginners: 4-6 weeks before progression
        - Intermediate: 6-8 weeks with periodic adjustments
        - Advanced: 8-12 weeks with planned periodization
        
        After this period, regenerate your plan with updated fitness level and goals.
        """)
    
    with st.expander("💡 Tips for success"):
        st.markdown("""
        **Maximize Your Results:**
        - ✅ Be consistent with your training schedule
        - ✅ Track your workouts and progress
        - ✅ Prioritize recovery and sleep
        - ✅ Stay hydrated (8-10 glasses of water daily)
        - ✅ Combine exercise with proper nutrition
        - ✅ Start conservatively and progress gradually
        - ✅ Don't skip warm-ups or cool-downs
        - ✅ Listen to your body and rest when needed
        """)
    
    # ============ FOOTER ============
    st.markdown("""
    <div class="footer">
        <p style="font-size: 1.1rem; color: #666; font-weight: 600; margin-bottom: 1rem;">💪 FriskaAI - Your AI Fitness Coach</p>
        <p style="color: #666; margin-bottom: 0.5rem;">Powered by Advanced AI | Evidence-Based Exercise Science | Medical Safety First</p>
        <p style="color: #999; font-size: 0.9rem;">© 2024 FriskaAI. For informational purposes only. Not a substitute for professional medical advice.</p>
        <p style="color: #999; font-size: 0.85rem; margin-top: 1rem;">
            <strong>Disclaimer:</strong> Always consult with a healthcare provider before beginning any exercise program.
            Stop immediately if you experience pain or discomfort.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============ RUN APPLICATION ============
if __name__ == "__main__":
    main()