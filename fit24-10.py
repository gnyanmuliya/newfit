import streamlit as st
import requests
import json
import os
import pandas as pd
from typing import Dict, List, Optional
import re
import random


condition_data = pd.read_excel("Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx")  # your Excel file
condition_data.fillna("", inplace=True)


# ---------------- CONFIG ----------------
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(page_title="FriskaAi - Smart Fitness Advisor", layout="wide")

# ---------------- MEDICAL CONDITIONS LIST ----------------
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

# ---------------- EXERCISE DATABASE ----------------
class ExerciseDatabase:
    def __init__(self):
        self.exercises = {
            "supine_dead_bug": {
                "name": "Supine Dead Bug",
                "type": "Core Stability",
                "equipment": ["Mat"],
                "level": "Beginner",
                "reps": "10-12 reps/side",
                "intensity": "RPE 3-4",
                "rest": "30-45 sec",
                "benefits": "Improves core control & lumbar stability",
                "target_areas": ["Core", "Stomach"],
                "rating": 4.5,
                "safety": "Keep a neutral spine and avoid excessive lumbar extension. Stop if you feel sharp back pain.",
                "contraindications": ["acute lower back pain", "recent spinal surgery", "severe disc herniation"],
                "steps": [
                    "Lie on your back with knees bent at 90 degrees",
                    "Extend opposite arm and leg slowly",
                    "Hold for 2-3 seconds",
                    "Return to starting position",
                    "Repeat on other side"
                ],
                "demo_video": "Core Exercise_ Dead Bug 1.mp4",
                "common_mistakes": ["Arching back", "Moving too fast", "Not engaging core"]
            },
            "supine_rotator_cuff": {
                "name": "Supine Rotator Cuff",
                "type": "Shoulder Stability",
                "equipment": ["Mat", "Small Cushion"],
                "level": "Beginner",
                "reps": "10-12 reps/arm",
                "intensity": "RPE 3-4",
                "rest": "30-45 sec",
                "benefits": "Strengthens rotator cuff & improves posture",
                "target_areas": ["Arms", "Back"],
                "rating": 4.2,
                "safety": "Move slowly and keep range small if you have shoulder pain.",
                "contraindications": ["acute rotator cuff tear", "recent shoulder surgery", "severe shoulder impingement"],
                "steps": [
                    "Lie on your side with arm at 90 degrees",
                    "Place cushion under head for support",
                    "Rotate forearm up slowly",
                    "Hold briefly, then lower",
                    "Complete all reps before switching sides"
                ],
                "demo_video": "4 Supine Rotator Cuff Movements 1.mp4",
                "common_mistakes": ["Using momentum", "Rotating too far", "Not supporting head"]
            },
            "upward_facing_dog": {
                "name": "Upward Facing Dog",
                "type": "Spinal Extension",
                "equipment": ["Mat"],
                "level": "Intermediate",
                "reps": "6-8 reps / 15-30 sec holds",
                "intensity": "RPE 4-6",
                "rest": "30-60 sec",
                "benefits": "Opens chest & improves spinal flexibility",
                "target_areas": ["Back", "Chest"],
                "rating": 4.7,
                "safety": "Avoid if you have acute low back pain or recent spinal injury.",
                "contraindications": ["acute lower back pain", "recent spinal surgery"],
                "steps": [
                    "Start in plank position",
                    "Lower hips while lifting chest",
                    "Straighten arms and lift thighs off ground",
                    "Hold for 15-30 seconds",
                    "Lower back to starting position"
                ],
                "demo_video": "How to Do Upward-Facing Dog Pose in Yoga 1.mp4",
                "common_mistakes": ["Sinking shoulders", "Overarching neck", "Not engaging legs"]
            },
            "v_ups": {
                "name": "V-Ups",
                "type": "Core Strength",
                "equipment": ["Mat"],
                "level": "Intermediate",
                "reps": "AMRAP or 8-12 reps",
                "intensity": "RPE 6-7",
                "rest": "60-90 sec",
                "benefits": "Builds core strength & coordination",
                "target_areas": ["Core", "Stomach"],
                "rating": 4.3,
                "safety": "Keep neck neutral and avoid jerking.",
                "contraindications": ["acute lower back pain", "hernia"],
                "steps": [
                    "Lie flat with arms overhead",
                    "Simultaneously lift legs and torso",
                    "Try to touch toes at the top",
                    "Lower slowly with control",
                    "Keep core engaged throughout"
                ],
                "demo_video": "v_ups_demo.mp4",
                "common_mistakes": ["Using momentum", "Not controlling descent", "Straining neck"]
            },
            "dirty_dog": {
                "name": "Dirty Dog",
                "type": "Glute Strength",
                "equipment": ["Mat"],
                "level": "Beginner",
                "reps": "10-12 reps/side",
                "intensity": "RPE 4-5",
                "rest": "45-60 sec",
                "benefits": "Strengthens glutes & improves hip mobility",
                "target_areas": ["Glutes", "Legs"],
                "rating": 4.4,
                "safety": "Keep core braced and avoid excessive lumbar rotation.",
                "contraindications": ["acute lower back pain"],
                "steps": [
                    "Start on hands and knees",
                    "Keep knee bent and lift leg to side",
                    "Lift until thigh is parallel to ground",
                    "Lower slowly without touching ground",
                    "Complete all reps before switching"
                ],
                "demo_video": "dirty_dog_demo.mp4",
                "common_mistakes": ["Lifting too high", "Rotating hips", "Not keeping core stable"]
            },
            "barbell_squat": {
                "name": "Barbell Squat",
                "type": "Compound Strength",
                "equipment": ["Barbell", "Squat Rack"],
                "level": "Intermediate",
                "reps": "8-12 reps",
                "intensity": "70-75% 1RM",
                "rest": "90-120 sec",
                "benefits": "Builds overall leg strength and power",
                "target_areas": ["Legs", "Glutes", "Core"],
                "rating": 4.8,
                "safety": "Use proper set-up and avoid deep squats if you have knee pain.",
                "contraindications": ["acute knee injury", "recent knee surgery", "severe lower back pain"],
                "steps": [
                    "Position bar on upper traps",
                    "Stand with feet shoulder-width apart",
                    "Lower by pushing hips back and bending knees",
                    "Descend until thighs parallel to floor",
                    "Drive through heels to return to start"
                ],
                "demo_video": "barbell_squat_demo.mp4",
                "common_mistakes": ["Knee valgus", "Forward lean", "Partial range of motion"]
            },
            "bench_press": {
                "name": "Bench Press",
                "type": "Upper Body Strength",
                "equipment": ["Barbell", "Bench"],
                "level": "Intermediate",
                "reps": "6-10 reps",
                "intensity": "70-80% 1RM",
                "rest": "90-180 sec",
                "benefits": "Develops chest, shoulders, and triceps strength",
                "target_areas": ["Chest", "Arms", "Shoulders"],
                "rating": 4.7,
                "safety": "Use a spotter for heavy loads.",
                "contraindications": ["acute shoulder injury", "recent shoulder surgery"],
                "steps": [
                    "Lie flat on bench with feet planted",
                    "Grip bar slightly wider than shoulders",
                    "Lower bar to chest with control",
                    "Press bar up in straight line",
                    "Lock out arms at the top"
                ],
                "demo_video": "bench_press_demo.mp4",
                "common_mistakes": ["Bouncing off chest", "Uneven grip", "Arched back"]
            }
        }
    
    def get_exercises_by_target_area(self, target_areas: List[str], workout_location: str = "Home") -> Dict:
        """Filter exercises by target body areas and location"""
        filtered = {}
        for key, exercise in self.exercises.items():
            if "Full Body" in target_areas:
                filtered[key] = exercise
                continue
            if any(area in exercise.get("target_areas", []) for area in target_areas):
                filtered[key] = exercise
        return filtered
    
    def get_exercises_by_equipment(self, available_equipment: List[str], workout_location: str = "Home") -> Dict:
        """Filter exercises by available equipment"""
        filtered = {}
        for key, exercise in self.exercises.items():
            if "large gym" in workout_location.lower():
                filtered[key] = exercise
                continue
            
            reqs = [e.lower() for e in exercise.get("equipment", [])]
            avail = [a.lower() for a in (available_equipment or [])]
            
            if "none" in reqs or "bodyweight only" in reqs or "mat" in reqs:
                filtered[key] = exercise
            elif all(r in avail for r in reqs):
                filtered[key] = exercise
        return filtered

    def is_contraindicated(self, exercise: Dict, medical_conditions: List[str]) -> bool:
        """Check if exercise is contraindicated for user's conditions"""
        if not medical_conditions or medical_conditions == ["None"]:
            return False
        ex_contras = [c.lower() for c in exercise.get("contraindications", [])]
        user_conds = [c.lower() for c in medical_conditions]
        
        for uc in user_conds:
            for ec in ex_contras:
                if ec in uc or uc in ec:
                    return True
        return False

# ---------------- FITNESS ADVISOR CLASS ----------------
class FitnessAdvisor:
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.exercise_db = ExerciseDatabase()
    
    """
Enhanced Fitness Plan Prompt Generation System
Inspired by meal plan prompting structure for consistent, safe workout outputs
"""

def build_fitness_plan_system_prompt(
    user_profile: dict,
    day_name: str,
    day_index: int,
    is_modification: bool = False,
    original_plan_context: str = None,
    specific_exercise_to_modify: str = None
) -> str:
    """
    Build comprehensive system prompt for workout plan generation
    
    Args:
        user_profile: Complete user fitness profile
        day_name: Name of the day (e.g., "Monday")
        day_index: Index for rotation logic
        is_modification: Whether this is modifying existing plan
        original_plan_context: Previous plan for modifications
        specific_exercise_to_modify: Specific exercise user wants to change
    """
    
    # Extract user data
    name = user_profile.get("name", "User")
    age = user_profile.get("age", 30)
    gender = user_profile.get("gender", "Male")
    fitness_level = user_profile.get("fitness_level", "Level 3 - Intermediate")
    primary_goal = user_profile.get("primary_goal", "General Fitness")
    target_areas = user_profile.get("target_areas", ["Full Body"])
    medical_conditions = user_profile.get("medical_conditions", ["None"])
    physical_limitations = user_profile.get("physical_limitations", "")
    location = user_profile.get("workout_location", "Home")
    available_equipment = user_profile.get("available_equipment", ["None - Bodyweight Only"])
    session_duration = user_profile.get("session_duration", "30-45 minutes")
    
    # Determine focus area for the day
    focus_area = target_areas[day_index % len(target_areas)]
    
    # Get condition-specific guidelines
    condition_guidelines = get_condition_guidelines(medical_conditions)
    
    # Build the comprehensive prompt
    prompt_parts = []
    
    # ==================== SECTION 0: IDENTITY & PRIMARY MISSION ====================
    prompt_parts.append("""
You are FriskaAI, a certified clinical exercise physiologist and ACSM-certified fitness program designer. Your primary mission is to create medically safe, evidence-based, and highly personalized workout plans. Your performance is evaluated on strict adherence to safety protocols, scientific exercise prescription principles, and user-specific adaptations. You MUST respond ONLY in English.
""")
    
    # ==================== SECTION 1: USER PROFILE ====================
    profile_details = f"""
**1. USER PROFILE & FITNESS PARAMETERS (Non-Negotiable):**

**Basic Information:**
- Name: {name}
- Age: {age} years
- Gender: {gender}
- Fitness Level: {fitness_level}
- Primary Goal: {primary_goal}
- Session Duration: {session_duration}
- Workout Location: {location}

**Target Focus for {day_name}:** {focus_area}

**Medical & Physical Status:**
- Medical Conditions: {', '.join(medical_conditions)}
- Physical Limitations: {physical_limitations if physical_limitations else 'None reported'}
- Doctor Clearance: {user_profile.get('doctor_clearance', 'Not specified')}

**Available Equipment:**
{', '.join(available_equipment)}

**Activity Profile:**
- Current Activity Level: {user_profile.get('current_activity', 'Not specified')}
- Previous Exercise Experience: {user_profile.get('previous_experience', 'Not specified')}
- Training Days per Week: {user_profile.get('days_per_week', 3)}
"""
    prompt_parts.append(profile_details)
    
    # ==================== SECTION 2: MEDICAL SAFETY RULES ====================
    if medical_conditions and medical_conditions != ["None"]:
        prompt_parts.append(f"""
**2. MEDICAL SAFETY RULES (ABSOLUTELY CRITICAL - HIGHEST PRIORITY):**

**Condition-Specific Exercise Guidelines:**
{condition_guidelines}

**MANDATORY SAFETY PROTOCOL:**
- You MUST cross-reference EVERY exercise against the user's medical conditions
- You MUST NOT include any exercise listed as "contraindicated" for their conditions
- You MUST prioritize "Modified/Safer Exercises" from the guidelines above
- You MUST include appropriate intensity limits based on medical conditions
- You MUST provide safety cues for every exercise that address the user's specific health concerns

**CRITICAL CHECK:** Before finalizing the workout, verify that NO contraindicated exercises are included. Including a contraindicated exercise is a complete failure of your primary safety mission.
""")
    else:
        prompt_parts.append("""
**2. GENERAL SAFETY RULES (MANDATORY):**
- While no medical conditions are reported, you MUST still prioritize safe exercise progression
- All exercises must be appropriate for the user's age and fitness level
- Include proper warm-up and cool-down protocols
- Provide clear safety cues to prevent injury
""")
    
    # ==================== SECTION 3: AGE-ADAPTIVE RULES ====================
    if age >= 60:
        age_rules = """
**3. AGE-ADAPTIVE TRAINING RULES (STRICT - SENIOR POPULATION):**

**CRITICAL AGE-BASED MODIFICATIONS (Age ≥ 60):**
- Treat as beginner-to-moderate intensity regardless of stated fitness level
- MANDATORY FOCUS: Fall prevention, balance, and functional independence
- Joint-friendly, low-impact movements are REQUIRED

**PROHIBITED Exercises (First 4-8 weeks):**
- NO jumping, plyometrics, or high-impact movements
- NO floor-based planks (use wall or elevated surface alternatives)
- NO heavy barbell work or max effort lifts
- NO exercises requiring rapid directional changes
- NO burpees, mountain climbers, or high-intensity interval movements

**REQUIRED Exercise Categories:**
- Balance work: MUST include 2-3 balance exercises per session
- Functional movements: Sit-to-stand, step-ups, supported squats
- Upper body: Wall push-ups, resistance band rows, light overhead presses
- Lower body: Chair-assisted squats, heel raises, lateral leg raises
- Core: Standing marches, seated twists, bird-dog variations

**Progression Protocol:**
- Week 1-2: Focus on movement quality and balance
- Week 3-4: Gradually increase repetitions (not weight)
- Week 5-6: Introduce light resistance bands
- Week 7+: Progress based on individual response

**Intensity Guidelines:**
- RPE: 3-5 (Light to Moderate)
- Never exceed RPE 6 in first month
- Prioritize control over speed or load
"""
    elif age >= 40:
        age_rules = """
**3. AGE-ADAPTIVE TRAINING RULES (Age 40-59):**

**Moderate Age-Based Considerations:**
- Enhanced focus on joint health and mobility
- Include adequate warm-up with joint preparation (5-7 minutes minimum)
- Emphasize eccentric control to protect joints
- Include flexibility work in every session

**Recommended Modifications:**
- Lower impact alternatives when appropriate
- Emphasize proper form over heavy loads
- Include balance exercises 2x per week
- Recovery: 48-72 hours between intense sessions for same muscle groups

**Intensity Guidelines:**
- RPE: 4-7 (Moderate to Moderately Hard)
- Progressive overload: Increase volume before intensity
"""
    else:
        age_rules = """
**3. AGE-ADAPTIVE TRAINING RULES (Age < 40):**

**Standard Adult Training Protocol:**
- Full range of exercise modalities available (if medically cleared)
- Can include higher-intensity options if fitness level permits
- Prioritize standing, functional movements over seated exercises
- Progressive overload based on fitness level

**Intensity Guidelines:**
- Beginner: RPE 4-6
- Intermediate: RPE 5-7
- Advanced: RPE 6-8
"""
    prompt_parts.append(age_rules)
    
    # ==================== SECTION 4: FITNESS LEVEL ADAPTATION ====================
    fitness_level_rules = """
**4. FITNESS LEVEL ADAPTATION (MANDATORY SCALING):**

**Level 1 - Assisted/Low Function:**
- Use chair support, wall support, or assisted variations for ALL exercises
- Sets: 1-2 sets × 6-10 reps
- Rest: 60-90 seconds between exercises
- Focus: Basic movement patterns, stability, confidence building
- RPE: 3-4 (Light effort)

**Level 2 - Beginner Functional:**
- Bodyweight exercises with minimal external load
- Sets: 2-3 sets × 8-12 reps
- Rest: 45-60 seconds
- Focus: Form mastery, basic strength foundation
- RPE: 4-6 (Light to Moderate)
- Equipment: Bodyweight, light resistance bands

**Level 3 - Moderate/Independent:**
- Can incorporate moderate resistance
- Sets: 3 sets × 10-15 reps
- Rest: 30-60 seconds
- Focus: Strength building, muscular endurance
- RPE: 5-7 (Moderate to Moderately Hard)
- Equipment: Dumbbells (5-20 lbs), resistance bands, bodyweight

**Level 4 - Active Wellness:**
- Progressive resistance training
- Sets: 3-4 sets × 8-12 reps
- Rest: 30-90 seconds (based on exercise complexity)
- Focus: Strength, power development, athletic performance
- RPE: 6-8 (Moderately Hard to Hard)
- Equipment: Full range available

**Level 5 - Adaptive Advanced:**
- Advanced training techniques (supersets, drop sets, tempo work)
- Sets: 3-4 sets × 6-15 reps (varied based on goal)
- Rest: 30-120 seconds (periodized)
- Focus: Performance optimization, specialized goals
- RPE: 7-9 (Hard to Very Hard)
- Equipment: Full range with progressive loading

**CRITICAL INSTRUCTION:** You MUST scale all exercises, sets, reps, and intensity to match the user's exact fitness level. Using advanced exercises for beginners or overly simple exercises for advanced users is a failure.
"""
    prompt_parts.append(fitness_level_rules)
    
    # ==================== SECTION 5: GOAL-SPECIFIC PROGRAMMING ====================
    goal_specific_rules = f"""
**5. GOAL-SPECIFIC PROGRAMMING (PRIMARY GOAL: {primary_goal}):**

"""
    
    # Add goal-specific guidelines
    if "Weight Loss" in primary_goal or "weight loss" in primary_goal.lower():
        goal_specific_rules += """
**Weight Loss Protocol:**
- Emphasize compound, multi-joint movements to maximize calorie burn
- Include metabolic conditioning (circuit training when appropriate)
- Higher rep ranges: 12-20 reps for most exercises
- Shorter rest periods: 30-45 seconds
- Include 5-10 minutes of steady-state cardio or active recovery between strength circuits
- Total workout should maintain elevated heart rate throughout
"""
    elif "Muscle Gain" in primary_goal or "muscle" in primary_goal.lower():
        goal_specific_rules += """
**Muscle Gain Protocol:**
- Focus on progressive overload with resistance
- Moderate rep ranges: 6-12 reps
- Longer rest periods: 60-120 seconds for compound lifts
- Emphasize eccentric (lowering) phase: 2-3 second tempo
- Include isolation exercises for target areas
- Volume: 12-20 sets per muscle group per week
"""
    elif "Strength" in primary_goal or "strength" in primary_goal.lower():
        goal_specific_rules += """
**Strength Building Protocol:**
- Prioritize compound movements (squats, deadlifts, presses, rows)
- Lower rep ranges: 4-8 reps
- Longer rest periods: 90-180 seconds
- Focus on load progression (if equipment available)
- Emphasize perfect form and controlled tempo
"""
    elif "Cardiovascular" in primary_goal or "cardio" in primary_goal.lower():
        goal_specific_rules += """
**Cardiovascular Fitness Protocol:**
- Include continuous movement patterns
- Mix of steady-state and interval work
- Higher rep ranges: 15-25 reps
- Minimal rest: 15-30 seconds
- Full-body movements preferred
- Target: Sustained elevated heart rate zones
"""
    elif "Flexibility" in primary_goal or "Mobility" in primary_goal:
        goal_specific_rules += """
**Flexibility & Mobility Protocol:**
- Dynamic stretching in warm-up (5-7 minutes)
- Active mobility drills throughout workout
- Include PNF stretching techniques when appropriate
- Static stretching in cool-down (8-10 minutes)
- Hold stretches: 30-60 seconds
- Focus on full range of motion in all exercises
"""
    elif "Rehabilitation" in primary_goal or "rehab" in primary_goal.lower():
        goal_specific_rules += """
**Rehabilitation Protocol:**
- CRITICAL: All exercises MUST be cleared by medical professional
- Phase-based progression (follow rehab stage guidelines)
- Pain-free range of motion ONLY
- Very conservative loading
- Focus on movement quality over quantity
- Include specific therapeutic exercises for injury area
- Frequent position changes to prevent compensation patterns
"""
    elif "Posture" in primary_goal or "Balance" in primary_goal:
        goal_specific_rules += """
**Posture & Balance Protocol:**
- Core stabilization exercises: MANDATORY in every session
- Posterior chain strengthening (back, glutes, hamstrings)
- Balance challenges progressing from static to dynamic
- Include proprioceptive training
- Scapular stabilization work
- Hip stability exercises
"""
    else:
        goal_specific_rules += """
**General Fitness Protocol:**
- Balanced approach across all fitness components
- Include strength, cardio, flexibility, and balance elements
- Moderate rep ranges: 10-15 reps
- Varied rest periods: 30-60 seconds
- Full-body functional movements preferred
"""
    
    prompt_parts.append(goal_specific_rules)
    
    # ==================== SECTION 6: WORKOUT STRUCTURE RULES ====================
    prompt_parts.append(f"""
**6. MANDATORY WORKOUT STRUCTURE (STRICT FORMAT):**

**YOU MUST GENERATE A COMPLETE WORKOUT WITH ALL FOUR SECTIONS. A workout missing any section is considered incomplete and unacceptable.**

**SECTION A: WARM-UP (5-7 minutes) - MANDATORY**
- MUST include 3-4 movements
- MUST be mobility and activation focused
- MUST NOT include strength exercises (no squats, push-ups, planks in warm-up)
- Appropriate warm-up movements: arm circles, leg swings, hip circles, cat-cow, shoulder rolls, ankle mobility, trunk rotations, marching in place, light dynamic stretches

**SECTION B: MAIN WORKOUT (4-6 exercises) - MANDATORY**
- MUST include {4 if session_duration == "15-20 minutes" else 5 if session_duration == "20-30 minutes" else 6} exercises
- MUST focus on: {focus_area}
- MUST alternate muscle groups when possible (e.g., upper/lower, push/pull)
- MUST NOT repeat exercises from warm-up or cool-down
- Each exercise MUST include: Exercise name, benefit, detailed steps, sets × reps, intensity (RPE), rest period, safety cue specific to user's profile

**SECTION C: COOL-DOWN (5-7 minutes) - MANDATORY**
- MUST include 3-4 movements
- MUST be stretching and breathing focused
- MUST NOT include strength exercises
- Appropriate cool-down movements: static stretches (hamstring, quad, chest, shoulder, hip flexor), child's pose (if appropriate for age/mobility), cat-cow, spinal twists, deep breathing exercises
- For users aged 60+: Use seated or standing stretches instead of floor-based poses unless mobility allows

**SECTION D: PROGRESSION NOTES - MANDATORY**
- Brief guidance on how to progress the workout in following weeks
- Adjustment recommendations based on user feedback

**FORMAT FOR EACH EXERCISE (MANDATORY):**
```
**Exercise Name**
- Benefit: [Specific benefit related to user goal]
- How to Perform:
  1. [Detailed step 1]
  2. [Detailed step 2]
  3. [Detailed step 3]
  4. [Additional steps as needed]
- Sets × Reps: [e.g., 3 × 10-12]
- Intensity: RPE [X-Y]
- Rest: [e.g., 45 seconds]
- Safety Cue: [Specific to user's age/condition/limitations]
- Modification: [Easier/harder variation if needed]
```
""")
    
    # ==================== SECTION 7: EXERCISE SELECTION RULES ====================
    prompt_parts.append(f"""
**7. EXERCISE SELECTION RULES (CRITICAL GUIDELINES):**

**Equipment-Based Selection:**
- User has access to: {', '.join(available_equipment)}
- You MUST ONLY select exercises that can be performed with available equipment
- If "None - Bodyweight Only": All exercises must be bodyweight or use household items (chair, towel, water bottles)
- If "Home": Prefer simple, space-efficient exercises
- If "Large Commercial Gym": Full exercise library is available

**Target Area Priority ({focus_area}):**
- At least 60-70% of main exercises MUST directly target: {focus_area}
- Include supporting muscle groups for balanced development
- Ensure proper warm-up for target area

**Movement Pattern Balance (CRITICAL):**
For every workout, ensure inclusion of these fundamental patterns (when applicable to focus area):
1. Push (vertical or horizontal)
2. Pull (vertical or horizontal)
3. Hinge (hip dominant)
4. Squat (knee dominant)
5. Core stabilization
6. Locomotion/Carry (when appropriate)

**Exercise Variety Rules:**
- NO repetition of the same exercise in warm-up, main workout, and cool-down
- Each training day in the week MUST have different exercises
- Use exercise variations to keep workouts fresh while targeting same areas

**Contraindication Check (MANDATORY):**
Before including ANY exercise, verify it is NOT contraindicated for:
- User's medical conditions
- User's physical limitations
- User's age-specific restrictions
- User's equipment limitations
""")
    
    # ==================== SECTION 8: INTENSITY & VOLUME RULES ====================
    prompt_parts.append("""
**8. INTENSITY & VOLUME PRESCRIPTION (SCIENTIFIC STANDARDS):**

**RPE (Rate of Perceived Exertion) Scale - 1-10:**
- 1-2: Very Light (minimal effort)
- 3-4: Light (can maintain conversation easily)
- 5-6: Moderate (can talk in short sentences)
- 7-8: Hard (difficult to speak)
- 9-10: Very Hard to Maximal (cannot maintain)

**Rest Period Guidelines:**
- Strength focus: 90-180 seconds
- Hypertrophy: 60-90 seconds
- Muscular endurance: 30-60 seconds
- Circuit/metabolic: 15-30 seconds
- Adjust based on fitness level: beginners need more rest

**Volume Guidelines by Fitness Level:**
- Level 1-2: Total sets per workout: 8-12 sets
- Level 3: Total sets per workout: 12-18 sets
- Level 4-5: Total sets per workout: 16-24 sets

**Progressive Overload Strategy:**
Week 1: Focus on form and establishing baseline
Week 2: Increase reps by 2-3
Week 3: Add additional set OR increase intensity
Week 4: Deload (reduce volume by 30-40%)
Week 5+: Increase resistance/difficulty OR reduce rest periods
""")
    
    # ==================== SECTION 9: OUTPUT FORMATTING ====================
    prompt_parts.append(f"""
**9. STRICT OUTPUT FORMATTING (ABSOLUTELY CRITICAL):**

**START YOUR RESPONSE WITH:**
"Here is your personalized workout for {day_name}, focusing on {focus_area}:"

**THEN PROVIDE THE WORKOUT IN THIS EXACT STRUCTURE:**

### {day_name} – {focus_area} Focus

**Warm-Up (5-7 minutes)**
[List 3-4 mobility/activation movements with duration]

**Main Workout (Target: {focus_area})**
[List 4-6 exercises with complete format specified in Section 6]

**Cool-Down (5-7 minutes)**
[List 3-4 stretches/breathing exercises with duration]

**Progression for Next Week:**
[Brief guidance]

**KEY SAFETY REMINDERS:**
[2-3 critical safety points specific to this user]

**FORMATTING RULES:**
- Use markdown headers with `###` for day and `**` for sections
- Each exercise must be on new lines with clear formatting
- Include blank lines between exercises for readability
- NO conversational text before or after the workout plan
- NO motivational fluff - be concise and professional
""")
    
    # ==================== SECTION 10: MODIFICATION HANDLING ====================
    if is_modification and original_plan_context:
        if specific_exercise_to_modify:
            prompt_parts.append(f"""
**10. MODIFICATION REQUEST (CRITICAL INSTRUCTION):**

**PRIMARY DIRECTIVE:** The user wants to modify this specific exercise: **{specific_exercise_to_modify}**
User's request: "{user_profile.get('modification_request', 'Not specified')}"

**MODIFICATION WORKFLOW:**

1. **SAFETY CHECK:**
   - Verify the requested modification doesn't violate medical conditions
   - Ensure new exercise is appropriate for fitness level
   - If unsafe, provide polite refusal with explanation

2. **MAINTAIN PLAN INTEGRITY:**
   - Keep all other exercises from original plan unchanged
   - Ensure new exercise fits the same movement pattern category
   - Maintain total workout volume and intensity

3. **PROVIDE MODIFIED PLAN:**
   - Show complete updated workout with the single exercise changed
   - Highlight what was changed
   - Explain why the new exercise is appropriate

**Original Workout Plan for Reference:**
{original_plan_context}

**Remember:** You can ONLY modify the specific exercise requested. All other elements remain the same.
""")
        else:
            prompt_parts.append(f"""
**10. GENERAL MODIFICATION REQUEST:**

User wants to update the workout with this request: "{user_profile.get('modification_request', 'Not specified')}"

**Original Workout Plan for Reference:**
{original_plan_context}

**MODIFICATION GUIDELINES:**
- Make ONLY the changes requested by the user
- Maintain safety and appropriateness for user's profile
- Keep overall workout structure and balance
- Provide complete updated workout plan
- Highlight what was changed
""")
    
    # ==================== SECTION 11: FINAL VERIFICATION ====================
    prompt_parts.append("""
**11. FINAL VERIFICATION CHECKLIST (MANDATORY BEFORE RESPONDING):**

Before providing your response, verify you have:
- [ ] Included ALL four mandatory sections: Warm-up, Main Workout, Cool-down, Progression Notes
- [ ] Checked that NO exercises violate medical contraindications
- [ ] Ensured exercises match user's available equipment
- [ ] Scaled intensity appropriately for fitness level
- [ ] Applied age-appropriate modifications
- [ ] Provided complete exercise instructions with safety cues
- [ ] Maintained focus on specified target area
- [ ] Aligned exercises with primary goal
- [ ] Used proper formatting with markdown
- [ ] Included NO unnecessary conversational text

**IF ANY ITEM IS UNCHECKED, YOU MUST REVISE YOUR PLAN BEFORE RESPONDING.**
""")
    
    # ==================== SECTION 12: TASK DIRECTIVE ====================
    if is_modification:
        task_directive = f"""
**12. YOUR TASK:**
Generate a MODIFIED workout plan for {day_name} that incorporates the user's requested changes while maintaining safety and effectiveness. Follow all rules above with special attention to the Modification Request section.
"""
    else:
        task_directive = f"""
**12. YOUR TASK:**
Generate a COMPLETE workout plan for {day_name} focusing on {focus_area} that adheres to ALL rules, guidelines, and formatting requirements specified above. This is a new plan generation - create a comprehensive, safe, and effective workout.
"""
    
    prompt_parts.append(task_directive)
    
    return "\n".join(prompt_parts)


def get_condition_guidelines(medical_conditions: list) -> str:
    """
    Generate detailed condition-specific exercise guidelines
    Similar to meal plan's condition data integration
    """
    if not medical_conditions or medical_conditions == ["None"]:
        return "No medical conditions reported. Standard exercise protocols apply."
    
    guidelines = []
    
    # This would integrate with your Excel data
    # For now, showing the structure
    condition_data_map = {
        "Hypertension": {
            "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing without control",
            "modified": "Controlled breathing, moderate resistance, avoid breath-holding",
            "intensity": "RPE 4-6, avoid RPE >7",
            "notes": "Monitor for dizziness, stop if experiencing headache or visual changes"
        },
        "Type 2 Diabetes": {
            "contraindicated": "High-intensity intervals without medical clearance, prolonged fasting exercise",
            "modified": "Moderate-intensity steady state, check blood glucose pre/post workout",
            "intensity": "RPE 5-7, progress gradually",
            "notes": "Have fast-acting carbs available, monitor for hypoglycemia signs"
        },
        "Osteoarthritis": {
            "contraindicated": "High-impact jumping, deep squats with pain, excessive joint loading",
            "modified": "Low-impact alternatives, partial range if painful, aquatic exercise preferred",
            "intensity": "RPE 3-6, pain-free range only",
            "notes": "Some mild discomfort acceptable, sharp pain is a stop signal"
        },
        "Osteoporosis": {
            "contraindicated": "Spinal flexion, high-impact if severe, twisting movements under load",
            "modified": "Weight-bearing activities, resistance training with proper form, balance work",
            "intensity": "RPE 4-6, progressive loading",
            "notes": "Focus on bone-strengthening exercises, avoid fall risk scenarios"
        },
        "Chronic Lower Back Pain": {
            "contraindicated": "Loaded spinal flexion, unsupported twisting, heavy deadlifts initially",
            "modified": "Core stabilization, neutral spine movements, progressive loading",
            "intensity": "RPE 3-5 initially, pain-free movement only",
            "notes": "Pain centralization is good, peripheralization requires modification"
        },
        # Add more conditions as needed
    }
    
    for condition in medical_conditions:
        for key, data in condition_data_map.items():
            if key.lower() in condition.lower():
                guideline = f"""
🏥 **{key}:**
   - ❌ Contraindicated Exercises: {data['contraindicated']}
   - ✅ Modified/Safer Exercises: {data['modified']}
   - 📊 Intensity Limit: {data['intensity']}
   - ⚠️ Special Notes: {data['notes']}
"""
                guidelines.append(guideline)
                break
    
    if not guidelines:
        return f"Medical conditions noted: {', '.join(medical_conditions)}\nNo specific exercise contraindications in database. Proceed with general precautions appropriate for reported conditions."
    
    return "\n".join(guidelines)


# Example usage:
if __name__ == "__main__":
    sample_profile = {
        "name": "John Smith",
        "age": 65,
        "gender": "Male",
        "fitness_level": "Level 2 - Beginner Functional",
        "primary_goal": "Improve Posture and Balance",
        "target_areas": ["Core", "Back", "Legs"],
        "medical_conditions": ["Hypertension (High Blood Pressure)", "Osteoarthritis"],
        "physical_limitations": "Mild knee pain on right side",
        "workout_location": "Home",
        "available_equipment": ["Mat", "Resistance Bands"],
        "session_duration": "30-45 minutes",
        "days_per_week": 3,
        "current_activity": "Lightly Active (light exercise 1-3 days/week)",
        "doctor_clearance": "Yes - I have clearance"
    }
    
    prompt = build_fitness_plan_system_prompt(
        user_profile=sample_profile,
        day_name="Monday",
        day_index=0,
        is_modification=False
    )
    
    print("=== GENERATED SYSTEM PROMPT ===")
    print(prompt)
    print("\n=== END OF PROMPT ===")

    def get_condition_guidelines(medical_conditions: list) -> str:
        """
        Generate detailed condition-specific exercise guidelines
        """
    # [Paste the function from document 2, lines 453-510]

    def assess_risk_flag(self, user_profile: Dict) -> str:
        """Return risk_flag: None, Low, Moderate, High"""
        medical = [c.lower() for c in (user_profile.get("medical_conditions") or [])]
        physical = (user_profile.get("physical_limitations") or "").lower()
        
        high_risk = ["heart", "recent surgery", "stroke", "heart failure", "uncontrolled hypertension"]
        moderate_risk = ["diabetes", "arthritis", "osteoporosis", "obesity", "copd"]
        
        for hr in high_risk:
            if any(hr in m for m in medical) or hr in physical:
                return "High"
        for mr in moderate_risk:
            if any(mr in m for m in medical) or mr in physical:
                return "Moderate"
        
        return "Low" if medical and medical != ["none"] else "None"

    def get_condition_guidelines(self, medical_conditions: List[str]) -> str:
        """Return full Excel-based instructions for each condition selected."""
        guidelines = []
        for cond in medical_conditions:
            matches = condition_data[condition_data["Condition"].str.contains(cond, case=False, na=False)]
            for _, row in matches.iterrows():
                guidelines.append(
                    f"🩺 Condition: {row['Condition']}\n"
                    f"- Contraindicated Exercises: {row['Contraindicated Exercises']}\n"
                    f"- Modified / Safer Exercises: {row['Modified / Safer Exercises']}\n"
                    f"- Exercise Type: {row['Exercise Type']}\n"
                    f"- Affected Body Region: {row['Affected Body Region']}\n"
                    f"- Intensity Limit: {row['Intensity Limit']}\n"
                )
        if not guidelines:
            return "No condition-specific restrictions or modifications."
        return "\n".join(guidelines)


    def generate_exclude_tags(self, user_profile: Dict) -> List[str]:
        """Generate exercise exclusion tags"""
        tags = set()
        med = " ".join((user_profile.get("medical_conditions") or [])).lower()
        phys = (user_profile.get("physical_limitations") or "").lower()
        
        if "back" in med or "back" in phys or "disc" in med:
            tags.add("avoid_spinal_flexion")
        if "hip" in phys or "knee" in phys or "fracture" in med:
            tags.add("avoid_high_impact")
        if "cardiac" in med or "heart" in med:
            tags.add("no_heavy_isometrics")
        
        return list(tags)

    def generate_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Generate one day's plan using full Excel condition data and fitness-level adaptation."""
        name = user_profile.get("name", "User")
        fitness_level = user_profile.get("fitness_level", "Level 3 - Intermediate")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        location = user_profile.get("workout_location", "Home")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        target_areas = user_profile.get("target_areas", ["Full Body"])

        # 🩺 Include full Excel-based condition guide
        condition_guidelines = self.get_condition_guidelines(medical_conditions)

        # 🎯 Determine daily focus area
        focus = target_areas[day_index % len(target_areas)]

        # 🧘 Fitness-level guidance
        if "Beginner" in fitness_level or "Level 1" in fitness_level or "Level 2" in fitness_level:
            intensity_instruction = (
                "For BEGINNERS: Avoid heavy lifts, high-impact moves, or long holds. "
                "Use bodyweight, light resistance, and focus on slow, controlled form."
            )
        elif "Intermediate" in fitness_level or "Level 3" in fitness_level:
            intensity_instruction = (
                "For INTERMEDIATE users: Moderate intensity allowed. Combine strength and mobility "
                "while maintaining good form and breathing."
            )
        else:
            intensity_instruction = (
                "For ADVANCED users: Include progressive overload, compound movements, and moderate-high intensity as appropriate."
            )

        # 🧠 Build the full instruction prompt
        prompt = f"""
    
You are FriskaAI, a certified clinical exercise physiologist and fitness program designer. Your job is to generate medically safe, goal-based workout plans.

### USER PROFILE
Name: {name}
Age: {user_profile.get('age')}
Goal: {primary_goal}
Experience Level: {fitness_level} (Beginner/Intermediate/Advanced only)
Training Days: {", ".join(user_profile.get("training_days", []))}
Location: {location}
Medical Conditions: {", ".join(medical_conditions)}
Focus Today: {focus}

### MEDICAL RULES (STRICT)
Use the following condition-specific restrictions and safe exercise recommendations:
{condition_guidelines}

- ONLY apply medical modification rules if the user has a medical condition.
- If NO medical condition: follow age-appropriate fitness progression instead of general population rules.


### GENERAL TRAINING RULES
- If age < 40 and no mobility issues → **NO seated/chair workouts**
- Warm-ups should be **mobility + activation**, not strength exercises
- Cool-downs should be **stretching + breathing**, not main exercises
- Every day MUST have different exercises (no repeating the same plan)
- Ensure push / pull / legs / core movement balance
- Prioritize functional standing movements unless medically restricted
### GENERAL TRAINING RULES
- Prioritize safety, joint protection, and controlled tempo
- Warm-ups must be mobility + activation (not strength drills)
- Cool-downs must be stretching + breathing (not main exercises)
- No repetition of warm-up/cool-down movements in main workout
- Maintain balance between push / pull / legs / core

### AGE-ADAPTIVE TRAINING RULES (STRICT)
If Age ≥ 60:
- Treat as beginner unless user explicitly states very active
- Use low-impact, joint-friendly movements
- Prioritize: sit-to-stand, wall push-ups, band rows, heel raises, step taps, marching, supported balance work
- Avoid for first 4 weeks:
  - Jumping or impact work (NO jumping jacks / jump squats)
  - Floor planks (use standing/bench supported core instead)
  - Heavy squats (use chair-assisted sit-to-stand)
  - Burpees, mountain climbers, HIIT moves
- Balance and fall-prevention must be included weekly
- Mobility before stability before strength progression

### AGE < 60 RULE
If age < 60 and no limitations → avoid seated or chair-based exercises unless goal is rehab

### NO CONDITION RULE UPDATE
If user has NO medical condition:
- Still follow age-appropriate exercise safety rules
- Senior guidelines override fitness level when needed
- Focus on foundational strength, mobility & balance

### INTENSITY RULES
Beginner = 
- Bodyweight + bands 
- 2–3 sets × 8–12 reps
- RPE 5–7
- Slow tempo & controlled breathing

Intermediate =
- Progressive overload allowed
- Dumbbells/bands ok
- RPE 6–8

Advanced =
- Higher volume & load
- Complex patterns allowed only if safe

### EQUIPMENT RULES
Home workout movement priority:
1. Bodyweight
2. Resistance band
3. Dumbbell (if user has)

### WORKOUT FORMAT (STRICT)
Format exactly as follows:

### {day_name} — {focus}

**Warm-Up (5 minutes)**
Warm-up must not include squats, planks, or strength movements. Only mobility:
Examples: marching in place, shoulder circles, ankle mobility, thoracic rotations, hip openers, diaphragmatic breathing
- 3 movements  
Format each:  
Movement — Benefit — Duration — Safety cue  
(Examples: arm circles, marching in place, hip openers, cat-cow, ankle mobilizations, breathing drills)

**Main Workout (4–6 exercises)**  
For each exercise:  
Exercise Name  
- Benefit
- Steps/How to do?  
- Sets x Reps  
- RPE/Intensity  
- Rest  
- Safety cue

Rules:  
- Must match user goal & fitness level  
- Must follow medical sheet when condition exists  
- Must alternate muscle groups if possible  

**Cool-Down (5 minutes)** 
Cool-down must not include yoga poses requiring hands/knees on floor unless user is under 60 and mobile.
- 3 movements  
Format each:  
Stretch / breathing drill — Benefit — Duration — Safety cue

### IMPORTANT SAFETY REQUIREMENTS
- NO seated/rehab-style movements unless medically required  
- NO repeating same day workout  
- Warm-ups = mobility/activation only  
- Cool-downs = stretching + breathing only  
- If condition has contraindicated exercises → strictly avoid  
- Prefer approved/safe exercises from Excel sheet  

Generate the workout ONLY. No motivational text, no duplication.
"""


        # --- Send to API ---
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": "fitness-advisor",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, a concise medical fitness expert."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1200,
            }
            resp = requests.post(self.endpoint_url, headers=headers, json=payload, timeout=40)
            if resp.status_code == 200:
                result = resp.json()
                choices = result.get("choices")
                if choices:
                    content = choices[0].get("message", {}).get("content") or choices[0].get("text")
                    if content:
                        return content.strip()
        except Exception as e:
            st.warning(f"API error for {day_name}: {e}")
            return self.generate_local_day_plan(user_profile, day_name, day_index)

        # fallback
        return self.generate_local_day_plan(user_profile, day_name, day_index)



    def generate_local_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Fallback local plan generator for one day"""
        target_areas = user_profile.get("target_areas", ["Full Body"])
        focus = target_areas[day_index % len(target_areas)]
        
        candidates = list(self.exercise_db.get_exercises_by_target_area([focus], 
                         user_profile.get("workout_location", "Home")).values())
        
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        safe_exercises = [ex for ex in candidates if not self.exercise_db.is_contraindicated(ex, medical_conditions)]
        
        if not safe_exercises:
            safe_exercises = list(self.exercise_db.exercises.values())[:5]
        
        safe_exercises = sorted(safe_exercises, key=lambda x: -x.get("rating", 0))[:5]
        
        plan = [f"### {day_name} - Focus: {focus}\n"]
        plan.append("**Warm-up (5 minutes):**")
        plan.append("- Jumping Jacks (2 min)")
        plan.append("- Arm Circles (1 min)")
        plan.append("- Leg Swings (2 min)\n")
        
        plan.append("**Main Workout:**\n")
        for i, ex in enumerate(safe_exercises, 1):
            plan.append(f"**{i}. {ex['name']}**")
            plan.append(f"- Benefit: {ex['benefits']}")
            plan.append(f"- Sets/Reps: {ex['reps']}")
            plan.append(f"- Intensity: {ex['intensity']}")
            plan.append(f"- Rest: {ex['rest']}")
            plan.append(f"- Safety: {ex['safety']}\n")
        
        plan.append("**Cool-down (5 minutes):**")
        plan.append("- Child's Pose (2 min)")
        plan.append("- Hamstring Stretch (2 min)")
        plan.append("- Shoulder Stretch (1 min)")
        
        return "\n".join(plan)

    def generate_full_plan(self, user_profile: Dict) -> str:
        """Generate complete workout plan day by day"""
        selected_days = user_profile.get("selected_days", ["Monday", "Wednesday", "Friday"])
        
        header = f"""# 🏋️‍♂️ Your Personalized Fitness Plan

**👋 Hey {user_profile.get('name', 'there')}!**

**📊 Your Profile:**
- Age: {user_profile.get('age')} | Fitness Level: {user_profile.get('fitness_level')}
- Primary Goal: {user_profile.get('primary_goal')}
- Training Schedule: {len(selected_days)} days/week ({', '.join(selected_days)})
- Location: {user_profile.get('workout_location')}

---

"""
        
        all_plans = [header]
        
        progress_placeholder = st.empty()
        
        for idx, day in enumerate(selected_days):
            progress_placeholder.info(f"⏳ Generating plan for {day}... ({idx+1}/{len(selected_days)})")
            day_plan = self.generate_day_plan(user_profile, day, idx)
            all_plans.append(day_plan)
            all_plans.append("\n---\n")

        
        progress_placeholder.success(f"✅ All {len(selected_days)} workout days generated!")
        
        footer = """
## 📈 Progression Tips
- Week 1-2: Focus on form and consistency
- Week 3-4: Increase reps by 2-3 or add 5% weight
- Week 5+: Add variations or increase intensity

## 💪 Stay Consistent!
Remember: Progress takes time. Listen to your body and adjust as needed.

## 💧 Hydration & Safety
- Drink water before, during, and after workouts
- Stop immediately if you feel sharp pain
- Consult your doctor if you have concerns
"""
        all_plans.append(footer)
        
        return "\n".join(all_plans)

# Initialize
fitness_advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)

# Initialize session state
if 'onboarding_step' not in st.session_state:
    st.session_state.onboarding_step = 0
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}

# Progress indicator
def show_progress():
    total_steps = 7
    current = st.session_state.onboarding_step
    progress = current / total_steps
    st.progress(progress)
    st.caption(f"Step {current} of {total_steps}")

# Navigation buttons
def nav_buttons(show_back=True, show_next=True, next_label="Next →"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if show_back and st.session_state.onboarding_step > 0:
            if st.button("← Back"):
                st.session_state.onboarding_step -= 1
                st.rerun()
    with col3:
        if show_next:
            if st.button(next_label, type="primary"):
                return True
    return False

# ============ STEP 0: WELCOME ============
if st.session_state.onboarding_step == 0:
    st.title("🏋️‍♂️ FriskaAi - Your Personal Fitness Advisor")
    st.markdown("---")
    
    st.markdown("""
    ### 👋 Welcome to FriskaAi!
    
    **Personalized health & function plan for special populations.**
    
    We create customized fitness programs that consider:
    - ✅ Your medical conditions and limitations
    - ✅ Your functional abilities and goals
    - ✅ Your available equipment and time
    - ✅ Safe progressions tailored to YOU
    
    This onboarding takes about **5-7 minutes** and will help us create the perfect plan.
    
    *Let's get started on your fitness journey!* 💪
    """)
    
    if st.button("🚀 Begin Onboarding", type="primary", use_container_width=True):
        st.session_state.onboarding_step = 1
        st.rerun()

# ============ STEP 1: BASIC INFORMATION + PHYSICAL MEASUREMENTS ============
elif st.session_state.onboarding_step == 1:
    st.title("👤 Step 1: Basic Information & Measurements")
    show_progress()
    st.markdown("*Tell us about yourself*")
    
    # Basic info
    name = st.text_input("What's your name?*", value=st.session_state.user_data.get('name', ''))
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age*", 16, 100, st.session_state.user_data.get('age', 25))
    with col2:
        gender = st.selectbox("Gender*", ["Male", "Female", "Other"], 
                             index=["Male", "Female", "Other"].index(st.session_state.user_data.get('gender', 'Male')))
    
    st.markdown("---")
    st.markdown("### 📏 Physical Measurements")
    
    col3, col4 = st.columns(2)
    
    with col3:
        unit_system = st.radio(
            "Measurement System*",
            ["Metric (kg, cm)", "Imperial (lbs, inches)"],
            index=0 if st.session_state.user_data.get('unit_system', "Metric (kg, cm)") == "Metric (kg, cm)" else 1
        )
    
    is_metric = "Metric" in unit_system
    
    col5, col6 = st.columns(2)
    
    with col5:
        if is_metric:
            height = st.number_input(
                "Height (cm)*", 
                100, 250, 
                st.session_state.user_data.get('height', 170),
                help="Enter your height in centimeters"
            )
        else:
            height = st.number_input(
                "Height (inches)*", 
                39, 98, 
                st.session_state.user_data.get('height', 67),
                help="Enter your height in inches"
            )
    
    with col6:
        if is_metric:
            weight = st.number_input(
                "Weight (kg)*", 
                30.0, 300.0, 
                st.session_state.user_data.get('weight', 70.0),
                step=0.5,
                help="Enter your weight in kilograms"
            )
        else:
            weight = st.number_input(
                "Weight (lbs)*", 
                66.0, 660.0, 
                st.session_state.user_data.get('weight', 154.0),
                step=0.5,
                help="Enter your weight in pounds"
            )
    
    # Calculate BMI
    if is_metric:
        bmi = weight / ((height / 100) ** 2)
    else:
        bmi = (weight / (height ** 2)) * 703
    
    bmi = round(bmi, 1)
    
    # BMI Category
    if bmi < 18.5:
        bmi_category = "Underweight"
        bmi_color = "blue"
    elif 18.5 <= bmi < 25:
        bmi_category = "Normal weight"
        bmi_color = "green"
    elif 25 <= bmi < 30:
        bmi_category = "Overweight"
        bmi_color = "orange"
    else:
        bmi_category = "Obese"
        bmi_color = "red"
    
    st.info(f"**Your BMI:** {bmi} ({bmi_category})")
    
    if nav_buttons(show_back=False):
        if name:
            st.session_state.user_data.update({
                'name': name, 
                'age': age, 
                'gender': gender,
                'unit_system': unit_system,
                'height': height,
                'weight': weight,
                'bmi': bmi,
                'bmi_category': bmi_category
            })
            st.session_state.onboarding_step = 2
            st.rerun()
        else:
            st.error("Please enter your name")

# ============ STEP 2: GOALS + TARGET AREAS ============
elif st.session_state.onboarding_step == 2:
    st.title("🎯 Step 2: Your Goals & Target Areas")
    show_progress()
    st.markdown("*What do you want to achieve?*")
    
    # Primary Goal
    goal_options = [
        "Weight Loss",
        "Muscle Gain",
        "Increase Overall Strength",
        "Improve Cardiovascular Fitness",
        "Improve Flexibility & Mobility",
        "Rehabilitation & Injury Prevention",
        "Improve Posture and Balance",
        "Other"
    ]
    
    primary_goal = st.selectbox(
        "Choose ONE primary goal*", 
        goal_options,
        index=0 if 'primary_goal' not in st.session_state.user_data else 
              goal_options.index(st.session_state.user_data.get('primary_goal', goal_options[0]))
    )
    
    # If "Other" is selected, show text input
    primary_goal_other = ""
    if primary_goal == "Other":
        primary_goal_other = st.text_input(
            "Please specify your primary goal*",
            value=st.session_state.user_data.get('primary_goal_other', ''),
            placeholder="e.g., Training for a marathon, recovering from surgery..."
        )
    
    # Secondary goals
    secondary_goal_options = [
        "Energy & Stamina",
        "Flexibility",
        "Stress Reduction",
        "Healthy Habits",
        "Confidence & Quality of Life",
        "Weight Management"
    ]
    
    secondary_goals = st.multiselect(
        "Secondary goals (optional, select multiple):",
        secondary_goal_options,
        default=st.session_state.user_data.get('secondary_goals', [])
    )
    
    st.markdown("---")
    st.markdown("### 🎯 Target Areas")
    st.markdown("*Which body areas do you want to focus on? (choose 1-3)*")
    
    target_options = [
        "Full Body", "Core", "Legs", "Arms", "Back", "Chest", 
        "Shoulders", "Glutes", "Stomach"
    ]
    
    target_areas = st.multiselect(
        "Target Areas:",
        target_options,
        default=st.session_state.user_data.get('target_areas', ["Full Body"])
    )
    
    if not target_areas:
        st.warning("Please select at least one target area")
    elif len(target_areas) > 3:
        st.info("💡 Tip: Focusing on 1-3 areas typically yields better results")
    
    # Special handling for Rehabilitation goal
    doctor_clearance = "Unknown"
    rehab_stage = None
    
    if "Rehabilitation" in primary_goal:
        st.info("⚕️ Rehabilitation requires medical clearance")
        doctor_clearance = st.selectbox("Doctor clearance?*", 
            ["Unknown", "Yes - I have clearance", "No - Not yet cleared"])
        if doctor_clearance == "Yes - I have clearance":
            rehab_stage = st.selectbox("Rehab Stage*", 
                ["Phase 1 (Early/Acute)", "Phase 2 (Progressive)", "Phase 3 (Advanced)"])
    
    if nav_buttons():
        # Validate based on primary goal selection
        if primary_goal == "Other" and not primary_goal_other:
            st.error("Please specify your primary goal")
        elif not target_areas:
            st.error("Please select at least one target area")
        else:
            final_primary_goal = primary_goal_other if primary_goal == "Other" else primary_goal
            st.session_state.user_data.update({
                'primary_goal': final_primary_goal,
                'secondary_goals': secondary_goals,
                'target_areas': target_areas,
                'doctor_clearance': doctor_clearance,
                'rehab_stage': rehab_stage
            })
            st.session_state.onboarding_step = 3
            st.rerun()

# ============ STEP 3: HEALTH & MEDICAL SCREENING ============
elif st.session_state.onboarding_step == 3:
    st.title("🥼 Step 3: Health & Medical Screening")
    show_progress()
    st.markdown("*This helps us create a safe program for you*")
    
    # Medical conditions selection
    medical_conditions = st.multiselect(
        "Select any medical conditions (select all that apply)*", 
        MEDICAL_CONDITIONS,
        default=st.session_state.user_data.get('medical_conditions', ["None"])
    )
    
    # If "Other" is selected, show text input
    medical_conditions_other = ""
    if "Other" in medical_conditions:
        medical_conditions_other = st.text_input(
            "Please specify your medical condition*",
            value=st.session_state.user_data.get('medical_conditions_other', ''),
            placeholder="e.g., Specific condition not listed above..."
        )
    
    # Current medications
    st.markdown("---")
    st.markdown("### 💊 Current Medications")
    
    taking_medications = st.radio(
        "Are you currently taking any medications?*",
        ["No", "Yes"],
        index=0 if st.session_state.user_data.get('taking_medications', 'No') == 'No' else 1
    )
    
    medications_list = ""
    if taking_medications == "Yes":
        medications_list = st.text_area(
            "Please list your medications (optional)",
            value=st.session_state.user_data.get('medications_list', ''),
            placeholder="e.g., Blood pressure medication, insulin, etc.",
            help="This helps us understand potential exercise interactions"
        )
    
    # Physical limitations
    st.markdown("---")
    st.markdown("### 🚫 Physical Limitations")
    
    physical_limitations = st.text_area(
        "Any injuries, pain, or physical limitations?*",
        value=st.session_state.user_data.get('physical_limitations', ''),
        placeholder="e.g., Lower back pain, knee injury, shoulder mobility issues...",
        help="Be specific about any areas that hurt or limit your movement"
    )
    
    if nav_buttons():
        # Validate "Other" medical condition
        if "Other" in medical_conditions and not medical_conditions_other:
            st.error("Please specify your medical condition")
        else:
            # Add "Other" condition to the list if specified
            final_medical_conditions = medical_conditions.copy()
            if "Other" in medical_conditions and medical_conditions_other:
                final_medical_conditions.remove("Other")
                final_medical_conditions.append(medical_conditions_other)
            
            st.session_state.user_data.update({
                'medical_conditions': final_medical_conditions,
                'taking_medications': taking_medications,
                'medications_list': medications_list,
                'physical_limitations': physical_limitations
            })
            st.session_state.onboarding_step = 4
            st.rerun()

# ============ STEP 4: ACTIVITY & LIFESTYLE + FITNESS LEVEL ============
elif st.session_state.onboarding_step == 4:
    st.title("📊 Step 4: Activity & Lifestyle Assessment")
    show_progress()
    st.markdown("*Help us understand your current fitness level*")
    
    # Current Activity Level (Dropdown)
    st.markdown("### 🏃 Current Activity Level")
    
    activity_level = st.selectbox(
        "How would you describe your current activity level?*",
        [
            "Sedentary (little to no exercise)",
            "Lightly Active (light exercise 1-2 days/week)",
            "Moderately Active (moderate exercise 3-4 days/week)",
            "Very Active (intense exercise 5-6 days/week)",
            "Extremely Active (intense daily exercise or physical job)"
        ],
        index=0 if 'activity_level' not in st.session_state.user_data else
              [
                  "Sedentary (little to no exercise)",
                  "Lightly Active (light exercise 1-2 days/week)",
                  "Moderately Active (moderate exercise 3-4 days/week)",
                  "Very Active (intense exercise 5-6 days/week)",
                  "Extremely Active (intense daily exercise or physical job)"
              ].index(st.session_state.user_data.get('activity_level'))
    )
    
    # Daily Stress Level (Dropdown)
    st.markdown("---")
    st.markdown("### 😰 Daily Stress Level")
    
    stress_level = st.selectbox(
        "How would you rate your daily stress level?*",
        [
            "Low (minimal stress, well-managed)",
            "Moderate (some stress, generally manageable)",
            "High (frequent stress, affecting daily life)",
            "Very High (constant stress, overwhelming)"
        ],
        index=0 if 'stress_level' not in st.session_state.user_data else
              [
                  "Low (minimal stress, well-managed)",
                  "Moderate (some stress, generally manageable)",
                  "High (frequent stress, affecting daily life)",
                  "Very High (constant stress, overwhelming)"
              ].index(st.session_state.user_data.get('stress_level', "Moderate (some stress, generally manageable)"))
    )
    
    # Sleep Quality
    col1, col2 = st.columns(2)
    
    with col1:
        sleep_hours = st.slider(
            "Average sleep hours per night*",
            4, 12, 
            st.session_state.user_data.get('sleep_hours', 7),
            help="Hours of sleep you typically get"
        )
    
    with col2:
        sleep_quality = st.selectbox(
            "Sleep quality*",
            ["Poor", "Fair", "Good", "Excellent"],
            index=["Poor", "Fair", "Good", "Excellent"].index(
                st.session_state.user_data.get('sleep_quality', 'Good')
            )
        )
    
    # Fitness Level Assessment (Dropdown - Level 1-5)
    st.markdown("---")
    st.markdown("### 💪 Fitness Level Assessment")
    
    fitness_level_descriptions = {
        "Level 1 - Beginner": "New to exercise or returning after long break. Need to build basic foundation.",
        "Level 2 - Early Intermediate": "Can do basic exercises with good form. Ready for slight progression.",
        "Level 3 - Intermediate": "Regular exerciser. Comfortable with most movements and moderate intensity.",
        "Level 4 - Advanced": "Experienced with various training methods. Can handle high intensity.",
        "Level 5 - Elite/Athlete": "Highly trained. Training at competitive or professional level."
    }
    
    fitness_level = st.selectbox(
        "Select your current fitness level*",
        list(fitness_level_descriptions.keys()),
        index=2 if 'fitness_level' not in st.session_state.user_data else
              list(fitness_level_descriptions.keys()).index(
                  st.session_state.user_data.get('fitness_level', 'Level 3 - Intermediate')
              ),
        help="Be honest - this ensures safe and effective programming"
    )
    
    st.info(f"**{fitness_level}:** {fitness_level_descriptions[fitness_level]}")
    
    # Previous Exercise Experience
    st.markdown("---")
    exercise_experience = st.text_area(
        "Previous exercise experience (optional)",
        value=st.session_state.user_data.get('exercise_experience', ''),
        placeholder="e.g., Played sports in college, did CrossFit for 2 years, yoga practitioner...",
        help="Tell us about your fitness background"
    )
    
    if nav_buttons():
        st.session_state.user_data.update({
            'activity_level': activity_level,
            'stress_level': stress_level,
            'sleep_hours': sleep_hours,
            'sleep_quality': sleep_quality,
            'fitness_level': fitness_level,
            'exercise_experience': exercise_experience
        })
        st.session_state.onboarding_step = 5
        st.rerun()

# ============ STEP 5: FITNESS ENVIRONMENT & CONSTRAINTS ============
elif st.session_state.onboarding_step == 5:
    st.title("🏠 Step 5: Fitness Environment & Constraints")
    show_progress()
    st.markdown("*Where and when will you train?*")
    
    # Workout Location
    st.markdown("### 📍 Workout Location")
    
    workout_location = st.selectbox(
        "Where will you primarily work out?*",
        ["Home", "Small Home Gym", "Large Gym/Fitness Center", "Outdoor", "Mixed (Various locations)"],
        index=0 if 'workout_location' not in st.session_state.user_data else
              ["Home", "Small Home Gym", "Large Gym/Fitness Center", "Outdoor", "Mixed (Various locations)"].index(
                  st.session_state.user_data.get('workout_location', 'Home')
              )
    )
    
    # Available Equipment
    st.markdown("---")
    st.markdown("### 🏋️ Available Equipment")
    
    equipment_options = [
        "None (Bodyweight only)",
        "Yoga Mat",
        "Resistance Band",
        "Resistance Bands",
        "Dumbbells",
        "Kettlebells",
        "Barbell & Plates",
        "Pull-up Bar",
        "Bench",
        "Squat Rack",
        "Cardio Machine (Treadmill/Bike)",
        "Full Gym Access"
    ]
    
    available_equipment = st.multiselect(
        "Select available equipment:",
        equipment_options,
        default=st.session_state.user_data.get('available_equipment', ["None (Bodyweight only)"])
    )
    
    # Workout Schedule
    st.markdown("---")
    st.markdown("### 📅 Workout Schedule")
    
    col1, col2 = st.columns(2)
    
    with col1:
        workout_frequency = st.selectbox(
            "How many days per week can you train?*",
            [2, 3, 4, 5, 6, 7],
            index=1 if 'workout_frequency' not in st.session_state.user_data else
                  [2, 3, 4, 5, 6, 7].index(st.session_state.user_data.get('workout_frequency', 3))
        )
    
    with col2:
        session_duration = st.selectbox(
            "How long per session?*",
            ["20-30 minutes", "30-45 minutes", "45-60 minutes", "60-90 minutes", "90+ minutes"],
            index=1 if 'session_duration' not in st.session_state.user_data else
                  ["20-30 minutes", "30-45 minutes", "45-60 minutes", "60-90 minutes", "90+ minutes"].index(
                      st.session_state.user_data.get('session_duration', '30-45 minutes')
                  )
        )
    
    # Preferred Days
    st.markdown("### 🗓️ Preferred Training Days")
    
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    selected_days = st.multiselect(
        "Select your preferred training days*",
        all_days,
        default=st.session_state.user_data.get('selected_days', all_days[:workout_frequency])
    )
    
    if len(selected_days) != workout_frequency:
        st.warning(f"⚠️ Please select exactly {workout_frequency} days")
    
    # Preferred Time
    preferred_time = st.selectbox(
        "Preferred workout time*",
        ["Morning (5-9 AM)", "Mid-Morning (9-12 PM)", "Afternoon (12-5 PM)", "Evening (5-9 PM)", "Night (9 PM+)", "Flexible"],
        index=0 if 'preferred_time' not in st.session_state.user_data else
              ["Morning (5-9 AM)", "Mid-Morning (9-12 PM)", "Afternoon (12-5 PM)", "Evening (5-9 PM)", "Night (9 PM+)", "Flexible"].index(
                  st.session_state.user_data.get('preferred_time', 'Morning (5-9 AM)')
              )
    )
    
    if nav_buttons():
        if len(selected_days) != workout_frequency:
            st.error(f"Please select exactly {workout_frequency} training days")
        else:
            st.session_state.user_data.update({
                'workout_location': workout_location,
                'available_equipment': available_equipment,
                'workout_frequency': workout_frequency,
                'session_duration': session_duration,
                'selected_days': selected_days,
                'preferred_time': preferred_time
            })
            st.session_state.onboarding_step = 6
            st.rerun()

# ============ STEP 6: FINAL REVIEW ============
elif st.session_state.onboarding_step == 6:
    st.title("✅ Step 6: Review Your Information")
    show_progress()
    st.markdown("*Please review your information before we generate your plan*")
    
    user_data = st.session_state.user_data
    
    # Personal Information
    with st.expander("👤 Personal Information", expanded=True):
        st.write(f"**Name:** {user_data.get('name')}")
        st.write(f"**Age:** {user_data.get('age')} years")
        st.write(f"**Gender:** {user_data.get('gender')}")
        st.write(f"**Height:** {user_data.get('height')} {'cm' if 'Metric' in user_data.get('unit_system') else 'inches'}")
        st.write(f"**Weight:** {user_data.get('weight')} {'kg' if 'Metric' in user_data.get('unit_system') else 'lbs'}")
        st.write(f"**BMI:** {user_data.get('bmi')} ({user_data.get('bmi_category')})")
    
    # Goals
    with st.expander("🎯 Goals & Target Areas", expanded=True):
        st.write(f"**Primary Goal:** {user_data.get('primary_goal')}")
        if user_data.get('secondary_goals'):
            st.write(f"**Secondary Goals:** {', '.join(user_data.get('secondary_goals'))}")
        st.write(f"**Target Areas:** {', '.join(user_data.get('target_areas', []))}")
    
    # Health Information
    with st.expander("🥼 Health & Medical Information", expanded=True):
        medical = user_data.get('medical_conditions', [])
        st.write(f"**Medical Conditions:** {', '.join(medical) if medical else 'None'}")
        st.write(f"**Taking Medications:** {user_data.get('taking_medications')}")
        if user_data.get('medications_list'):
            st.write(f"**Medications:** {user_data.get('medications_list')}")
        limitations = user_data.get('physical_limitations', '')
        st.write(f"**Physical Limitations:** {limitations if limitations else 'None reported'}")
    
    # Activity & Fitness
    with st.expander("📊 Activity & Fitness Level", expanded=True):
        st.write(f"**Activity Level:** {user_data.get('activity_level')}")
        st.write(f"**Stress Level:** {user_data.get('stress_level')}")
        st.write(f"**Sleep:** {user_data.get('sleep_hours')} hours/night ({user_data.get('sleep_quality')} quality)")
        st.write(f"**Fitness Level:** {user_data.get('fitness_level')}")
        if user_data.get('exercise_experience'):
            st.write(f"**Experience:** {user_data.get('exercise_experience')}")
    
    # Workout Setup
    with st.expander("🏋️ Fitness Environment & Schedule", expanded=True):
        st.write(f"**Location:** {user_data.get('workout_location')}")
        st.write(f"**Equipment:** {', '.join(user_data.get('available_equipment', []))}")
        st.write(f"**Frequency:** {user_data.get('workout_frequency')} days/week")
        st.write(f"**Session Duration:** {user_data.get('session_duration')}")
        st.write(f"**Training Days:** {', '.join(user_data.get('selected_days', []))}")
        st.write(f"**Preferred Time:** {user_data.get('preferred_time')}")
    
    st.markdown("---")
    st.info("💡 **Tip:** You can go back to edit any information using the '← Back' button")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Edit", use_container_width=True):
            st.session_state.onboarding_step -= 1
            st.rerun()
    
    with col2:
        if st.button("✨ Generate My Plan", type="primary", use_container_width=True):
            st.session_state.onboarding_step = 7
            st.rerun()

# ============ STEP 7: GENERATE & DISPLAY PLAN ============
elif st.session_state.onboarding_step == 7:
    st.title("🎉 Your Personalized Fitness Plan")
    show_progress()
    
    # Generate plan if not already generated
    if 'fitness_plan' not in st.session_state:
        with st.spinner("🔮 Creating your personalized fitness plan..."):
            fitness_plan = fitness_advisor.generate_full_plan(st.session_state.user_data)
            st.session_state.fitness_plan = fitness_plan
    
    # Display the plan
    st.markdown(st.session_state.fitness_plan)
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download Plan", use_container_width=True):
            st.download_button(
                label="Download as Text File",
                data=st.session_state.fitness_plan,
                file_name=f"FriskaAi_Plan_{st.session_state.user_data.get('name', 'User')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    with col2:
        if st.button("🔄 Start Over", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    with col3:
        if st.button("✏️ Modify Profile", use_container_width=True):
            st.session_state.onboarding_step = 1
            if 'fitness_plan' in st.session_state:
                del st.session_state['fitness_plan']
            st.rerun()
    
    # Feedback section
    st.markdown("---")
    st.markdown("### 💬 How do you like your plan?")
    
    feedback = st.text_area(
        "Share your feedback (optional)",
        placeholder="Let us know what you think about your personalized plan...",
        key="feedback_text"
    )
    
    if st.button("Submit Feedback", type="secondary"):
        st.success("Thank you for your feedback! 🙏")
    
    st.markdown("---")
    st.markdown("""
    ### 🚀 Next Steps
    1. **Save your plan** for easy reference
    2. **Start with Week 1** and focus on form
    3. **Track your progress** weekly
    4. **Listen to your body** and adjust as needed
    5. **Stay consistent** - results take time!
    
    ### 📞 Need Help?
    - Consult your doctor before starting any new exercise program
    - Work with a certified trainer for proper form guidance
    - Stop immediately if you experience sharp pain
    
    **Good luck on your fitness journey! 💪**
    """)