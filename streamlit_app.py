import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import hashlib
import json

# Page configuration
st.set_page_config(
    page_title="BuffaloMitra - AI-Powered Dairy Management",
    page_icon="🐃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Anthropic client
@st.cache_resource
def get_anthropic_client():
    try:
        from anthropic import Anthropic
        api_key = None
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except KeyError:
            try:
                api_key = st.secrets["api_keys"]["ANTHROPIC_API_KEY"]
            except KeyError:
                st.error("Could not find ANTHROPIC_API_KEY in secrets.")
                return None
        if api_key:
            return Anthropic(api_key=api_key)
        else:
            st.error("ANTHROPIC_API_KEY is empty")
            return None
    except ImportError:
        st.error("anthropic package not installed. Check requirements.txt")
        return None
    except Exception as e:
        st.error(f"Error initializing AI: {str(e)}")
        return None

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        color: #1565C0;
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-radius: 15px;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #0D47A1;
        font-weight: bold;
        margin-top: 1.5rem;
        border-bottom: 3px solid #2196F3;
        padding-bottom: 0.5rem;
    }
    .info-card {
        background-color: #E3F2FD;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid #2196F3;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .health-card {
        background-color: #E8F5E9;
        padding: 1.2rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .ai-card {
        background-color: #FFF3E0;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid #FF9800;
        margin: 1rem 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .alert-card {
        background-color: #FFEBEE;
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #F44336;
        margin: 0.8rem 0;
    }
    .success-card {
        background-color: #E8F5E9;
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin: 0.8rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Buffalo Breed Database
BUFFALO_BREEDS = {
    "Murrah": {
        "origin": "Punjab, Haryana",
        "avg_milk_yield_liters_per_day": "10-15",
        "peak_yield_liters": "18-22",
        "lactation_period_days": "280-305",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-16",
        "first_calving_age_months": "36-40",
        "body_weight_kg": "500-650",
        "characteristics": "Black color, tightly curled horns, wedge-shaped body",
        "price_range_inr": "₹80,000-1,50,000",
        "maintenance_level": "Medium",
        "heat_tolerance": "Good",
        "disease_resistance": "High",
        "suitable_regions": ["Punjab", "Haryana", "Maharashtra", "Gujarat", "Rajasthan"]
    },
    "Mehsana": {
        "origin": "Gujarat",
        "avg_milk_yield_liters_per_day": "8-12",
        "peak_yield_liters": "15-18",
        "lactation_period_days": "270-300",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-15",
        "first_calving_age_months": "38-42",
        "body_weight_kg": "450-550",
        "characteristics": "Black to grey color, medium horns",
        "price_range_inr": "₹60,000-1,20,000",
        "maintenance_level": "Low",
        "heat_tolerance": "Excellent",
        "disease_resistance": "High",
        "suitable_regions": ["Gujarat", "Rajasthan", "Maharashtra"]
    },
    "Jaffarabadi": {
        "origin": "Gujarat",
        "avg_milk_yield_liters_per_day": "10-14",
        "peak_yield_liters": "18-20",
        "lactation_period_days": "280-300",
        "fat_percentage": "7-9%",
        "snf_percentage": "9-11%",
        "calving_interval_months": "15-17",
        "first_calving_age_months": "40-45",
        "body_weight_kg": "600-800",
        "characteristics": "Large sized, black color, massive build",
        "price_range_inr": "₹1,00,000-2,00,000",
        "maintenance_level": "High",
        "heat_tolerance": "Good",
        "disease_resistance": "Medium",
        "suitable_regions": ["Gujarat", "Maharashtra", "Karnataka"]
    },
    "Surti": {
        "origin": "Gujarat",
        "avg_milk_yield_liters_per_day": "7-10",
        "peak_yield_liters": "12-15",
        "lactation_period_days": "270-290",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-15",
        "first_calving_age_months": "36-40",
        "body_weight_kg": "400-500",
        "characteristics": "Small to medium size, light colored",
        "price_range_inr": "₹50,000-1,00,000",
        "maintenance_level": "Low",
        "heat_tolerance": "Excellent",
        "disease_resistance": "High",
        "suitable_regions": ["Gujarat", "Maharashtra", "Rajasthan"]
    },
    "Nagpuri": {
        "origin": "Maharashtra",
        "avg_milk_yield_liters_per_day": "6-9",
        "peak_yield_liters": "12-14",
        "lactation_period_days": "260-280",
        "fat_percentage": "7-8%",
        "snf_percentage": "9-10%",
        "calving_interval_months": "14-16",
        "first_calving_age_months": "38-42",
        "body_weight_kg": "450-550",
        "characteristics": "Well adapted to Maharashtra climate",
        "price_range_inr": "₹45,000-90,000",
        "maintenance_level": "Low",
        "heat_tolerance": "Excellent",
        "disease_resistance": "High",
        "suitable_regions": ["Maharashtra", "Madhya Pradesh"]
    }
}

# Feed Database
FEED_DATABASE = {
    "Green_Fodder": {
        "items": ["Berseem", "Maize", "Jowar", "Bajra", "Lucerne", "Napier Grass", "Guinea Grass"],
        "requirement_kg_per_day": "25-35",
        "cost_per_kg": "₹2-4",
        "benefits": "High moisture, good palatability, rich in vitamins"
    },
    "Dry_Fodder": {
        "items": ["Wheat Straw", "Paddy Straw", "Sorghum Stover", "Groundnut Haulms"],
        "requirement_kg_per_day": "8-12",
        "cost_per_kg": "₹3-5",
        "benefits": "Bulk feed, provides fiber"
    },
    "Concentrate": {
        "items": ["Cattle Feed", "Cotton Seed Cake", "Groundnut Cake", "Soybean Meal", "Maize", "Wheat Bran"],
        "requirement_kg_per_day": "3-5 (based on milk yield)",
        "cost_per_kg": "₹20-35",
        "formula": "1 kg concentrate per 2.5 liters milk production",
        "benefits": "High energy, protein, increases milk yield"
    },
    "Mineral_Mixture": {
        "items": ["Commercial Mineral Mix", "Salt"],
        "requirement_kg_per_day": "0.05-0.1",
        "cost_per_kg": "₹40-60",
        "benefits": "Prevents deficiencies, improves reproduction"
    }
}

# Disease Database
DISEASE_DATABASE = {
    "Mastitis": {
        "type": "Bacterial",
        "symptoms": ["Swollen udder", "Hot and painful quarter", "Watery or clotted milk", "Reduced milk yield"],
        "prevention": ["Proper milking hygiene", "Teat dipping", "Clean environment", "Regular udder examination"],
        "treatment": ["Antibiotics (Veterinary)", "Strip milking", "Hot fomentation", "Anti-inflammatory drugs"],
        "critical": True
    },
    "Foot and Mouth Disease": {
        "type": "Viral",
        "symptoms": ["Fever", "Blisters in mouth and feet", "Drooling", "Lameness", "Reduced feed intake"],
        "prevention": ["Vaccination (twice yearly)", "Isolation of sick animals", "Farm biosecurity"],
        "treatment": ["Supportive care", "Wound care", "Soft feed", "Consult veterinarian immediately"],
        "critical": True
    },
    "Hemorrhagic Septicemia": {
        "type": "Bacterial",
        "symptoms": ["High fever", "Difficulty breathing", "Swelling in throat", "Sudden death"],
        "prevention": ["Annual vaccination", "Avoid waterlogging", "Good hygiene"],
        "treatment": ["Emergency veterinary care", "Antibiotics", "Supportive therapy"],
        "critical": True
    },
    "Repeat Breeding": {
        "type": "Reproductive",
        "symptoms": ["Regular heat but no conception", "More than 3 AI attempts fail"],
        "prevention": ["Proper nutrition", "Minerals supplementation", "Timely AI", "Health check-up"],
        "treatment": ["Hormonal therapy", "Uterine infection treatment", "Veterinary examination"],
        "critical": False
    },
    "Bloat": {
        "type": "Digestive",
        "symptoms": ["Distended left side", "Difficulty breathing", "Restlessness", "Stop ruminating"],
        "prevention": ["Gradual diet change", "Avoid wet green fodder", "Provide dry roughage"],
        "treatment": ["Stomach tube", "Bloat oil", "Walking", "Emergency: veterinary puncture"],
        "critical": True
    }
}

# Government Schemes
GOVERNMENT_SCHEMES = {
    "National_Dairy_Plan": {
        "name": "National Dairy Plan (NDP)",
        "benefit": "Productivity enhancement, breed improvement",
        "eligibility": "Dairy farmers, cooperatives",
        "how_to_apply": "Through State Implementing Agencies",
        "contact": "https://www.nddb.coop"
    },
    "Dairy_Entrepreneurship_Development": {
        "name": "Dairy Entrepreneurship Development Scheme (DEDS)",
        "benefit": "Subsidy for dairy units (25-33%)",
        "eligibility": "Individual/group wanting to start dairy",
        "how_to_apply": "Through NABARD",
        "contact": "https://www.nabard.org"
    },
    "Rashtriya_Gokul_Mission": {
        "name": "Rashtriya Gokul Mission",
        "benefit": "Breed conservation, development",
        "eligibility": "Farmers with indigenous breeds",
        "how_to_apply": "Through State Animal Husbandry Department",
        "contact": "State AH Department"
    },
    "Kisan_Credit_Card_Dairy": {
        "name": "Kisan Credit Card (Dairy)",
        "benefit": "Credit for dairy farming at 4% interest",
        "eligibility": "All dairy farmers",
        "how_to_apply": "Any bank",
        "contact": "Nearest bank branch"
    }
}

# Database initialization
def init_database():
    conn = sqlite3.connect('buffalomitra.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  full_name TEXT NOT NULL,
                  mobile TEXT NOT NULL,
                  email TEXT,
                  district TEXT,
                  village TEXT,
                  user_type TEXT DEFAULT 'Dairy Farmer',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS buffalo_inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  tag_number TEXT UNIQUE,
                  name TEXT,
                  breed TEXT,
                  date_of_birth DATE,
                  purchase_date DATE,
                  purchase_price REAL,
                  current_lactation INTEGER DEFAULT 0,
                  status TEXT DEFAULT 'Active',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS milk_production
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  date DATE,
                  morning_yield REAL,
                  evening_yield REAL,
                  total_yield REAL,
                  fat_percentage REAL,
                  price_per_liter REAL,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS breeding_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  breeding_date DATE,
                  breeding_type TEXT,
                  bull_details TEXT,
                  expected_calving_date DATE,
                  actual_calving_date DATE,
                  calf_gender TEXT,
                  pregnancy_status TEXT DEFAULT 'Bred',
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS health_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buffalo_id INTEGER,
                  date DATE,
                  record_type TEXT,
                  disease_name TEXT,
                  symptoms TEXT,
                  treatment TEXT,
                  medicine TEXT,
                  veterinarian TEXT,
                  cost REAL,
                  follow_up_date DATE,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id),
                  FOREIGN KEY(buffalo_id) REFERENCES buffalo_inventory(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS feed_management
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date DATE,
                  feed_type TEXT,
                  quantity_kg REAL,
                  cost_per_kg REAL,
                  total_cost REAL,
                  supplier TEXT,
                  notes TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS financial_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date DATE,
                  category TEXT,
                  transaction_type TEXT,
                  amount REAL,
                  description TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS milk_buyers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  buyer_name TEXT,
                  contact TEXT,
                  price_per_liter REAL,
                  payment_terms TEXT,
                  active BOOLEAN DEFAULT 1,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, full_name, mobile, email, district, village, user_type='Dairy Farmer'):
    try:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute('''INSERT INTO users (username, password_hash, full_name, mobile, email, 
                     district, village, user_type)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (username, password_hash, full_name, mobile, email, district, village, user_type))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, str(e)

def authenticate_user(username, password):
    conn = sqlite3.connect('buffalomitra.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('''SELECT id, username, full_name, mobile, email, district, village, user_type
                 FROM users WHERE username=? AND password_hash=?''',
              (username, password_hash))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            'id': user[0], 'username': user[1], 'full_name': user[2],
            'mobile': user[3], 'email': user[4], 'district': user[5],
            'village': user[6], 'user_type': user[7]
        }
    return None

def get_ai_response(user_message, context=""):
    client = get_anthropic_client()
    if not client:
        return "AI Assistant is not configured. Please add ANTHROPIC_API_KEY to secrets."
    
    try:
        user_data = st.session_state.get('user_data', {})
        location = f"{user_data.get('village', 'Unknown')}, {user_data.get('district', 'India')}"
        
        system_prompt = f"""You are BuffaloMitra AI, an expert buffalo dairy farming advisor.

Current farmer context:
- Location: {location}

You provide:
1. Buffalo breed selection and management advice
2. Feeding and nutrition recommendations
3. Breeding and reproduction guidance
4. Disease prevention and treatment advice
5. Milk production optimization
6. Financial and business advice for dairy farming
7. Government schemes and subsidies information

Always be:
- Practical and actionable
- Specific to Indian dairy farming conditions
- Supportive and encouraging
- Data-driven with realistic expectations

{context}"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

# Session state initialization
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def main():
    init_database()
    st.markdown('<div class="main-header">🐃 BuffaloMitra - AI Powered Dairy Management</div>', unsafe_allow_html=True)
    st.markdown("### संपूर्ण म्हैस व्यवस्थापन प्रणाली | Complete Buffalo Dairy Management System")
    
    if st.session_state.user_data is None:
        show_auth_page()
    else:
        show_main_app()

def show_auth_page():
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown("### Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submitted:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user_data = user
                        st.success(f"Welcome {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Please fill all fields")
    
    with tab2:
        st.markdown("### Create Account")
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*")
                new_password = st.text_input("Password* (min 6 chars)", type="password")
                full_name = st.text_input("Full Name*")
                mobile = st.text_input("Mobile* (10 digits)")
            with col2:
                email = st.text_input("Email")
                district = st.text_input("District*")
                village = st.text_input("Village*")
                user_type = st.selectbox("I am a", ["Dairy Farmer", "Buyer/Trader", "Veterinarian"])
            
            submitted = st.form_submit_button("Register", use_container_width=True, type="primary")
            
            if submitted:
                if not all([new_username, new_password, full_name, mobile, district, village]):
                    st.error("Please fill all required fields")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif not mobile.isdigit() or len(mobile) != 10:
                    st.error("Please enter valid 10-digit mobile")
                else:
                    success, result = create_user(new_username, new_password, full_name, mobile, 
                                                 email, district, village, user_type)
                    if success:
                        st.success("Account created! Please login")
                        st.balloons()
                    else:
                        st.error(f"Error: {result}")

def show_main_app():
    user = st.session_state.user_data
    
    with st.sidebar:
        st.markdown(f"### {user['full_name']}")
        st.markdown(f"**{user['village']}, {user['district']}**")
        st.markdown("---")
        
        pages = [
            "Dashboard",
            "AI Assistant",
            "Buffalo Inventory",
            "Milk Production Tracker",
            "Breeding Manager",
            "Health Records",
            "Feed Management",
            "Breed Information",
            "Disease Guide",
            "Milk Price Tracker",
            "Financial Manager",
            "Profit Calculator",
            "Government Schemes",
            "Buyer Connect",
            "Insurance Calculator"
        ]
        
        st.markdown("### Navigation")
        for page in pages:
            if st.button(page, key=f"nav_{page}", use_container_width=True, 
                        type="primary" if st.session_state.current_page == page else "secondary"):
                st.session_state.current_page = page
                st.rerun()
        
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.user_data = None
            st.session_state.current_page = "Dashboard"
            st.rerun()
    
    # Page routing
    page = st.session_state.current_page
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "AI Assistant":
        show_ai_assistant()
    elif page == "Buffalo Inventory":
        show_buffalo_inventory()
    elif page == "Milk Production Tracker":
        show_milk_production()
    elif page == "Breeding Manager":
        show_breeding_manager()
    elif page == "Health Records":
        show_health_records()
    elif page == "Feed Management":
        show_feed_management()
    elif page == "Breed Information":
        show_breed_information()
    elif page == "Disease Guide":
        show_disease_guide()
    elif page == "Milk Price Tracker":
        show_milk_price_tracker()
    elif page == "Financial Manager":
        show_financial_manager()
    elif page == "Profit Calculator":
        show_profit_calculator()
    elif page == "Government Schemes":
        show_government_schemes()
    elif page == "Buyer Connect":
        show_buyer_connect()
    elif page == "Insurance Calculator":
        show_insurance_calculator()

def show_dashboard():
    user = st.session_state.user_data
    st.markdown(f"### Welcome, {user['full_name']}!")
    
    # Get statistics
    conn = sqlite3.connect('buffalomitra.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM buffalo_inventory WHERE user_id=? AND status='Active'", (user['id'],))
    total_buffalo = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM buffalo_inventory WHERE user_id=? AND current_lactation>0 AND status='Active'", (user['id'],))
    lactating = c.fetchone()[0]
    
    c.execute("""SELECT SUM(total_yield) FROM milk_production 
                 WHERE user_id=? AND date=?""", (user['id'], datetime.now().date()))
    today_milk = c.fetchone()[0] or 0
    
    c.execute("""SELECT AVG(total_yield) FROM milk_production 
                 WHERE user_id=? AND date >= date('now', '-30 days')""", (user['id'],))
    avg_daily = c.fetchone()[0] or 0
    
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Buffaloes", total_buffalo)
    with col2:
        st.metric("Lactating", lactating)
    with col3:
        st.metric("Today's Milk", f"{today_milk:.1f} L")
    with col4:
        st.metric("30-Day Avg", f"{avg_daily:.1f} L/day")
    
    # Quick actions
    st.markdown("### Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Record Milk", use_container_width=True):
            st.session_state.current_page = "Milk Production Tracker"
            st.rerun()
    with col2:
        if st.button("Add Buffalo", use_container_width=True):
            st.session_state.current_page = "Buffalo Inventory"
            st.rerun()
    with col3:
        if st.button("Health Check", use_container_width=True):
            st.session_state.current_page = "Health Records"
            st.rerun()
    with col4:
        if st.button("Ask AI", use_container_width=True):
            st.session_state.current_page = "AI Assistant"
            st.rerun()
    
    # Recent milk production chart
    st.markdown("### Milk Production Trend (Last 30 Days)")
    conn = sqlite3.connect('buffalomitra.db')
    df = pd.read_sql_query(
        """SELECT date, SUM(total_yield) as total 
           FROM milk_production 
           WHERE user_id=? AND date >= date('now', '-30 days')
           GROUP BY date ORDER BY date""",
        conn, params=(user['id'],))
    conn.close()
    
    if not df.empty:
        fig = px.line(df, x='date', y='total', title='Daily Milk Production',
                     labels={'total': 'Milk (Liters)', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No production data yet. Start recording milk production!")

def show_ai_assistant():
    st.markdown("### AI Dairy Assistant")
    st.markdown("Ask me anything about buffalo dairy farming!")
    
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f'<div class="info-card"><strong>You:</strong> {message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-card"><strong>BuffaloMitra AI:</strong> {message["content"]}</div>', 
                       unsafe_allow_html=True)
    
    st.markdown("### Quick Questions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Best buffalo breed for my area", use_container_width=True):
            question = f"What is the best buffalo breed for {st.session_state.user_data['district']}?"
            with st.spinner("Thinking..."):
                response = get_ai_response(question)
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    with col2:
        if st.button("How to increase milk yield", use_container_width=True):
            question = "What are the best practices to increase milk yield in buffaloes?"
            with st.spinner("Analyzing..."):
                response = get_ai_response(question)
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    with col3:
        if st.button("Disease prevention tips", use_container_width=True):
            question = "What are essential disease prevention practices for buffalo dairy farming?"
            with st.spinner("Searching..."):
                response = get_ai_response(question)
                st.session_state.chat_history.append({"role": "user", "content": question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("Your question:", placeholder="E.g., How much concentrate feed should I give?", height=100)
        submitted = st.form_submit_button("Send", use_container_width=True, type="primary")
        
        if submitted and user_input:
            with st.spinner("Getting answer..."):
                response = get_ai_response(user_input)
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    if st.session_state.chat_history:
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

def show_buffalo_inventory():
    st.markdown("### Buffalo Inventory")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["My Buffaloes", "Add New Buffalo"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name, breed, date_of_birth, current_lactation, status 
                     FROM buffalo_inventory WHERE user_id=? ORDER BY tag_number""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            for buf in buffaloes:
                age = (datetime.now().date() - datetime.strptime(str(buf[4]), '%Y-%m-%d').date()).days // 365
                with st.expander(f"🐃 {buf[2]} (Tag: {buf[1]}) - {buf[3]}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Age:** {age} years")
                        st.write(f"**Breed:** {buf[3]}")
                    with col2:
                        st.write(f"**Lactation:** {buf[5]}")
                        st.write(f"**Status:** {buf[6]}")
                    with col3:
                        st.write(f"**DOB:** {buf[4]}")
        else:
            st.info("No buffaloes added yet. Add your first buffalo below!")
    
    with tab2:
        st.markdown("### Add New Buffalo")
        with st.form("add_buffalo"):
            col1, col2 = st.columns(2)
            with col1:
                tag_number = st.text_input("Tag/ID Number*")
                name = st.text_input("Name")
                breed = st.selectbox("Breed*", list(BUFFALO_BREEDS.keys()))
                dob = st.date_input("Date of Birth*")
            with col2:
                purchase_date = st.date_input("Purchase Date")
                purchase_price = st.number_input("Purchase Price (₹)", min_value=0, value=100000)
                current_lactation = st.number_input("Current Lactation Number", min_value=0, value=0)
            
            submitted = st.form_submit_button("Add Buffalo", use_container_width=True, type="primary")
            
            if submitted and tag_number and breed:
                conn = sqlite3.connect('buffalomitra.db')
                c = conn.cursor()
                try:
                    c.execute("""INSERT INTO buffalo_inventory 
                                (user_id, tag_number, name, breed, date_of_birth, 
                                 purchase_date, purchase_price, current_lactation, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')""",
                             (user['id'], tag_number, name, breed, dob, 
                              purchase_date, purchase_price, current_lactation))
                    conn.commit()
                    st.success(f"Buffalo {name or tag_number} added successfully!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Tag number already exists!")
                finally:
                    conn.close()

def show_milk_production():
    st.markdown("### Milk Production Tracker")
    user = st.session_state.user_data
    
    tab1, tab2, tab3 = st.tabs(["Record Production", "View Records", "Analysis"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name, breed FROM buffalo_inventory 
                     WHERE user_id=? AND current_lactation>0 AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("record_milk"):
                buffalo_options = {f"{b[1]} - {b[2]} ({b[3]})": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date", value=datetime.now())
                    morning_yield = st.number_input("Morning Yield (Liters)", min_value=0.0, value=5.0, step=0.1)
                    evening_yield = st.number_input("Evening Yield (Liters)", min_value=0.0, value=5.0, step=0.1)
                with col2:
                    fat_percentage = st.number_input("Fat %", min_value=0.0, max_value=15.0, value=7.5, step=0.1)
                    price_per_liter = st.number_input("Price per Liter (₹)", min_value=0, value=60)
                    notes = st.text_input("Notes")
                
                submitted = st.form_submit_button("Record", use_container_width=True, type="primary")
                
                if submitted:
                    total_yield = morning_yield + evening_yield
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO milk_production 
                                (user_id, buffalo_id, date, morning_yield, evening_yield, 
                                 total_yield, fat_percentage, price_per_liter, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (user['id'], buffalo_id, date, morning_yield, evening_yield,
                              total_yield, fat_percentage, price_per_liter, notes))
                    conn.commit()
                    conn.close()
                    st.success(f"Recorded: {total_yield:.1f} liters")
                    st.rerun()
        else:
            st.warning("No lactating buffaloes. Update buffalo lactation status in inventory.")
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT mp.date, bi.tag_number, bi.name, mp.morning_yield, 
               mp.evening_yield, mp.total_yield, mp.fat_percentage, mp.price_per_liter
               FROM milk_production mp
               JOIN buffalo_inventory bi ON mp.buffalo_id = bi.id
               WHERE mp.user_id=? 
               ORDER BY mp.date DESC LIMIT 100""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            total_milk = df['total_yield'].sum()
            avg_fat = df['fat_percentage'].mean()
            total_value = (df['total_yield'] * df['price_per_liter']).sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Milk", f"{total_milk:.1f} L")
            with col2:
                st.metric("Avg Fat %", f"{avg_fat:.2f}%")
            with col3:
                st.metric("Total Value", f"₹{total_value:,.0f}")
        else:
            st.info("No production records yet")
    
    with tab3:
        st.markdown("### Production Analysis")
        
        conn = sqlite3.connect('buffalomitra.db')
        df_analysis = pd.read_sql_query(
            """SELECT date, SUM(total_yield) as daily_total, AVG(fat_percentage) as avg_fat
               FROM milk_production 
               WHERE user_id=? AND date >= date('now', '-90 days')
               GROUP BY date ORDER BY date""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df_analysis.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_analysis['date'], y=df_analysis['daily_total'],
                                name='Daily Milk', yaxis='y', marker_color='lightblue'))
            fig.add_trace(go.Scatter(x=df_analysis['date'], y=df_analysis['avg_fat'],
                                    name='Fat %', yaxis='y2', mode='lines+markers',
                                    line=dict(color='orange', width=2)))
            
            fig.update_layout(
                title='Milk Production & Fat % Trend',
                xaxis=dict(title='Date'),
                yaxis=dict(title='Milk (Liters)', side='left'),
                yaxis2=dict(title='Fat %', side='right', overlaying='y'),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)

def show_breed_information():
    st.markdown("### Buffalo Breed Information")
    
    breed_name = st.selectbox("Select Breed", list(BUFFALO_BREEDS.keys()))
    breed = BUFFALO_BREEDS[breed_name]
    
    st.markdown(f"## {breed_name}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Daily Yield", breed['avg_milk_yield_liters_per_day'] + " L")
        st.metric("Peak Yield", breed['peak_yield_liters'] + " L")
        st.metric("Fat %", breed['fat_percentage'])
    with col2:
        st.metric("Lactation Period", breed['lactation_period_days'] + " days")
        st.metric("Calving Interval", breed['calving_interval_months'] + " months")
        st.metric("First Calving Age", breed['first_calving_age_months'] + " months")
    with col3:
        st.metric("Body Weight", breed['body_weight_kg'] + " kg")
        st.metric("Price Range", breed['price_range_inr'])
        st.metric("Heat Tolerance", breed['heat_tolerance'])
    
    st.markdown("### Characteristics")
    st.info(breed['characteristics'])
    
    st.markdown("### Suitability")
    st.success(f"**Suitable Regions:** {', '.join(breed['suitable_regions'])}")
    st.write(f"**Maintenance Level:** {breed['maintenance_level']}")
    st.write(f"**Disease Resistance:** {breed['disease_resistance']}")
    
    if st.button("Get AI Advice for This Breed", type="primary"):
        with st.spinner("Getting detailed information..."):
            prompt = f"""Provide comprehensive information about {breed_name} buffalo breed:
            
            Include:
            1. Ideal housing and management practices
            2. Feeding requirements for optimal milk production
            3. Common health issues and prevention
            4. Breeding recommendations
            5. Economics of rearing this breed
            6. Tips for maximizing profitability
            
            Be specific and practical for Indian dairy farmers."""
            
            response = get_ai_response(prompt)
            st.markdown('<div class="ai-card">', unsafe_allow_html=True)
            st.markdown(f"### Complete Guide: {breed_name}")
            st.markdown(response)
            st.markdown('</div>', unsafe_allow_html=True)

def show_disease_guide():
    st.markdown("### Disease Guide")
    
    for disease_name, disease in DISEASE_DATABASE.items():
        with st.expander(f"{'🔴' if disease['critical'] else '🟡'} {disease_name} ({disease['type']})"):
            st.markdown("#### Symptoms")
            for symptom in disease['symptoms']:
                st.write(f"- {symptom}")
            
            st.markdown("#### Prevention")
            for prevention in disease['prevention']:
                st.success(f"✓ {prevention}")
            
            st.markdown("#### Treatment")
            for treatment in disease['treatment']:
                st.info(f"• {treatment}")
            
            if disease['critical']:
                st.error("⚠️ This is a critical disease. Consult veterinarian immediately!")

def show_breeding_manager():
    st.markdown("### Breeding Manager")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Record Breeding", "Breeding Calendar"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("record_breeding"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    breeding_date = st.date_input("Breeding Date")
                    breeding_type = st.selectbox("Breeding Type", ["Natural", "AI"])
                    bull_details = st.text_input("Bull Details/Breed")
                with col2:
                    expected_calving = breeding_date + timedelta(days=310)
                    st.date_input("Expected Calving Date", value=expected_calving, disabled=True)
                    notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Record", use_container_width=True, type="primary")
                
                if submitted:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO breeding_records 
                                (user_id, buffalo_id, breeding_date, breeding_type, 
                                 bull_details, expected_calving_date, pregnancy_status, notes)
                                VALUES (?, ?, ?, ?, ?, ?, 'Bred', ?)""",
                             (user['id'], buffalo_id, breeding_date, breeding_type,
                              bull_details, expected_calving, notes))
                    conn.commit()
                    conn.close()
                    st.success("Breeding recorded!")
                    st.rerun()
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT br.breeding_date, bi.tag_number, bi.name, br.breeding_type,
               br.expected_calving_date, br.pregnancy_status
               FROM breeding_records br
               JOIN buffalo_inventory bi ON br.buffalo_id = bi.id
               WHERE br.user_id=? AND br.pregnancy_status IN ('Bred', 'Pregnant')
               ORDER BY br.expected_calving_date""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            st.markdown("### Upcoming Calvings")
            for _, row in df.iterrows():
                days_to_calving = (datetime.strptime(str(row['expected_calving_date']), '%Y-%m-%d').date() - datetime.now().date()).days
                if 0 <= days_to_calving <= 30:
                    st.warning(f"🔔 {row['name']} ({row['tag_number']}) - Expected in {days_to_calving} days")

def show_health_records():
    st.markdown("### Health Records")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add Record", "View History"])
    
    with tab1:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        c.execute("""SELECT id, tag_number, name FROM buffalo_inventory 
                     WHERE user_id=? AND status='Active'""", (user['id'],))
        buffaloes = c.fetchall()
        conn.close()
        
        if buffaloes:
            with st.form("health_record"):
                buffalo_options = {f"{b[1]} - {b[2]}": b[0] for b in buffaloes}
                selected = st.selectbox("Select Buffalo", list(buffalo_options.keys()))
                buffalo_id = buffalo_options[selected]
                
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date")
                    record_type = st.selectbox("Type", ["Vaccination", "Treatment", "Checkup", "Deworming"])
                    disease_name = st.text_input("Disease/Condition")
                    symptoms = st.text_area("Symptoms")
                with col2:
                    treatment = st.text_area("Treatment Given")
                    medicine = st.text_input("Medicine")
                    veterinarian = st.text_input("Veterinarian")
                    cost = st.number_input("Cost (₹)", min_value=0, value=0)
                
                submitted = st.form_submit_button("Save Record", use_container_width=True, type="primary")
                
                if submitted:
                    conn = sqlite3.connect('buffalomitra.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO health_records 
                                (user_id, buffalo_id, date, record_type, disease_name, 
                                 symptoms, treatment, medicine, veterinarian, cost)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (user['id'], buffalo_id, date, record_type, disease_name,
                              symptoms, treatment, medicine, veterinarian, cost))
                    conn.commit()
                    conn.close()
                    st.success("Health record saved!")
                    st.rerun()
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        df = pd.read_sql_query(
            """SELECT hr.date, bi.tag_number, bi.name, hr.record_type, 
               hr.disease_name, hr.treatment, hr.cost
               FROM health_records hr
               JOIN buffalo_inventory bi ON hr.buffalo_id = bi.id
               WHERE hr.user_id=? 
               ORDER BY hr.date DESC""",
            conn, params=(user['id'],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.metric("Total Health Expense", f"₹{df['cost'].sum():,.0f}")

def show_feed_management():
    st.markdown("### Feed Management Guide")
    
    st.markdown("### Feeding Schedule")
    
    for feed_type, feed_info in FEED_DATABASE.items():
        with st.expander(f"📦 {feed_type.replace('_', ' ')}"):
            st.write(f"**Items:** {', '.join(feed_info['items'])}")
            st.write(f"**Daily Requirement:** {feed_info['requirement_kg_per_day']} kg")
            st.write(f"**Cost:** {feed_info['cost_per_kg']}")
            st.write(f"**Benefits:** {feed_info['benefits']}")
            
            if 'formula' in feed_info:
                st.info(f"**Formula:** {feed_info['formula']}")
    
    st.markdown("### Feed Calculator")
    num_buffaloes = st.number_input("Number of Buffaloes", min_value=1, value=1)
    avg_milk_yield = st.number_input("Average Milk Yield per Buffalo (L/day)", min_value=0.0, value=10.0)
    
    if st.button("Calculate Feed Requirement", type="primary"):
        green_fodder = 30 * num_buffaloes
        dry_fodder = 10 * num_buffaloes
        concentrate = (avg_milk_yield / 2.5) * num_buffaloes
        mineral = 0.075 * num_buffaloes
        
        st.markdown("### Daily Feed Requirement")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Green Fodder", f"{green_fodder:.0f} kg")
        with col2:
            st.metric("Dry Fodder", f"{dry_fodder:.0f} kg")
        with col3:
            st.metric("Concentrate", f"{concentrate:.1f} kg")
        with col4:
            st.metric("Mineral Mix", f"{mineral:.2f} kg")
        
        daily_cost = (green_fodder * 3) + (dry_fodder * 4) + (concentrate * 25) + (mineral * 50)
        monthly_cost = daily_cost * 30
        
        st.success(f"**Daily Feed Cost:** ₹{daily_cost:,.0f}")
        st.info(f"**Monthly Feed Cost:** ₹{monthly_cost:,.0f}")

def show_milk_price_tracker():
    st.markdown("### Milk Price Tracker")
    user = st.session_state.user_data
    
    st.markdown("### Current Market Rates (Maharashtra)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Dairy Company", "₹55-65/L")
        st.caption("Based on fat %")
    with col2:
        st.metric("Local Market", "₹70-85/L")
        st.caption("Direct to consumer")
    with col3:
        st.metric("Cooperative", "₹58-68/L")
        st.caption("Based on SNF & fat")
    
    st.markdown("### Price Calculator")
    fat_percent = st.slider("Fat %", 3.0, 12.0, 7.5, 0.1)
    snf_percent = st.slider("SNF %", 7.0, 11.0, 9.0, 0.1)
    
    base_price = 40
    fat_rate = 8
    snf_rate = 6
    
    calculated_price = base_price + (fat_percent * fat_rate) + (snf_percent * snf_rate)
    
    st.success(f"**Estimated Price:** ₹{calculated_price:.2f} per liter")
    
    st.markdown("### Price by District")
    st.info("""
    **Typical Prices:**
    - Pune: ₹60-70/L
    - Mumbai: ₹70-85/L
    - Nagpur: ₹55-65/L
    - Nashik: ₹58-68/L
    - Ahmednagar: ₹55-65/L
    
    *Prices vary based on fat %, SNF %, and local demand*
    """)

def show_financial_manager():
    st.markdown("### Financial Manager")
    user = st.session_state.user_data
    
    tab1, tab2 = st.tabs(["Add Transaction", "Financial Summary"])
    
    with tab1:
        with st.form("add_transaction"):
            col1, col2 = st.columns(2)
            with col1:
                transaction_type = st.selectbox("Type", ["Income", "Expense"])
                category = st.selectbox("Category", 
                    ["Milk Sale", "Buffalo Sale", "Feed", "Medicine", "Veterinary", 
                     "Equipment", "Labor", "Other"])
                amount = st.number_input("Amount (₹)", min_value=0, value=1000)
            with col2:
                date = st.date_input("Date", value=datetime.now())
                description = st.text_area("Description")
            
            submitted = st.form_submit_button("Add", use_container_width=True, type="primary")
            
            if submitted:
                conn = sqlite3.connect('buffalomitra.db')
                c = conn.cursor()
                c.execute("""INSERT INTO financial_records 
                            (user_id, date, category, transaction_type, amount, description)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                         (user['id'], date, category, transaction_type, amount, description))
                conn.commit()
                conn.close()
                st.success("Transaction added!")
                st.rerun()
    
    with tab2:
        conn = sqlite3.connect('buffalomitra.db')
        c = conn.cursor()
        
        c.execute("""SELECT transaction_type, SUM(amount) FROM financial_records 
                     WHERE user_id=? GROUP BY transaction_type""", (user['id'],))
        summary = dict(c.fetchall())
        conn.close()
        
        total_income = summary.get('Income', 0)
        total_expense = summary.get('Expense', 0)
        net_profit = total_income - total_expense
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Income", f"₹{total_income:,.0f}")
        with col2:
            st.metric("Total Expenses", f"₹{total_expense:,.0f}")
        with col3:
            st.metric("Net Profit", f"₹{net_profit:,.0f}")

def show_profit_calculator():
    st.markdown("### Profit Calculator")
    
    st.markdown("### Income")
    num_buffaloes = st.number_input("Number of Lactating Buffaloes", min_value=1, value=5)
    avg_milk = st.number_input("Average Milk per Buffalo (L/day)", min_value=0.0, value=10.0)
    milk_price = st.number_input("Milk Price (₹/L)", min_value=0, value=60)
    
    daily_milk = num_buffaloes * avg_milk
    daily_income = daily_milk * milk_price
    monthly_income = daily_income * 30
    
    st.markdown("### Expenses")
    feed_cost_per_buffalo = st.number_input("Feed Cost per Buffalo (₹/day)", min_value=0, value=250)
    medicine_monthly = st.number_input("Medicine & Veterinary (₹/month)", min_value=0, value=3000)
    labor_monthly = st.number_input("Labor Cost (₹/month)", min_value=0, value=10000)
    other_monthly = st.number_input("Other Expenses (₹/month)", min_value=0, value=5000)
    
    monthly_feed = feed_cost_per_buffalo * num_buffaloes * 30
    monthly_expense = monthly_feed + medicine_monthly + labor_monthly + other_monthly
    
    monthly_profit = monthly_income - monthly_expense
    annual_profit = monthly_profit * 12
    roi = (annual_profit / (monthly_expense * 12)) * 100 if monthly_expense > 0 else 0
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Monthly Income", f"₹{monthly_income:,.0f}")
    with col2:
        st.metric("Monthly Expense", f"₹{monthly_expense:,.0f}")
    with col3:
        st.metric("Monthly Profit", f"₹{monthly_profit:,.0f}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Annual Profit", f"₹{annual_profit:,.0f}")
    with col2:
        st.metric("ROI", f"{roi:.1f}%")

def show_government_schemes():
    st.markdown("### Government Schemes")
    
    for scheme_id, scheme in GOVERNMENT_SCHEMES.items():
        with st.expander(f"📋 {scheme['name']}"):
            st.markdown(f"**Benefit:** {scheme['benefit']}")
            st.markdown(f"**Eligibility:** {scheme['eligibility']}")
            st.markdown(f"**How to Apply:** {scheme['how_to_apply']}")
            st.markdown(f"**Contact:** {scheme['contact']}")

def show_buyer_connect():
    st.markdown("### Buyer Connect")
    user = st.session_state.user_data
    
    st.markdown("### Register Milk Buyer")
    with st.form("register_buyer"):
        col1, col2 = st.columns(2)
        with col1:
            buyer_name = st.text_input("Buyer Name")
            contact = st.text_input("Contact Number")
        with col2:
            price_per_liter = st.number_input("Price per Liter (₹)", min_value=0, value=60)
            payment_terms = st.text_input("Payment Terms", value="Weekly")
        
        submitted = st.form_submit_button("Register", use_container_width=True, type="primary")
        
        if submitted and buyer_name and contact:
            conn = sqlite3.connect('buffalomitra.db')
            c = conn.cursor()
            c.execute("""INSERT INTO milk_buyers 
                        (user_id, buyer_name, contact, price_per_liter, payment_terms, active)
                        VALUES (?, ?, ?, ?, ?, 1)""",
                     (user['id'], buyer_name, contact, price_per_liter, payment_terms))
            conn.commit()
            conn.close()
            st.success("Buyer registered!")
            st.rerun()

def show_insurance_calculator():
    st.markdown("### Livestock Insurance Calculator")
    
    num_buffaloes = st.number_input("Number of Buffaloes to Insure", min_value=1, value=5)
    avg_value = st.number_input("Average Value per Buffalo (₹)", min_value=10000, value=100000)
    
    total_sum_insured = num_buffaloes * avg_value
    premium_rate = 3.0  # 3% typical premium
    annual_premium = total_sum_insured * (premium_rate / 100)
    govt_subsidy = annual_premium * 0.5  # 50% subsidy
    farmer_premium = annual_premium - govt_subsidy
    
    st.markdown("### Insurance Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sum Insured", f"₹{total_sum_insured:,.0f}")
    with col2:
        st.metric("Your Premium", f"₹{farmer_premium:,.0f}")
    with col3:
        st.metric("Govt Subsidy", f"₹{govt_subsidy:,.0f}")
    
    st.success("""
    **Coverage Includes:**
    - Death due to accident
    - Death due to disease
    - Death due to natural calamity
    - In-transit deaths
    - Surgical operations
    
    **Apply through:** Any bank or insurance company
    """)

if __name__ == "__main__":
    main()