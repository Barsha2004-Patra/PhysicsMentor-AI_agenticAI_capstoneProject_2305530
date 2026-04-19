# 🧠 PhysicsMentor AI  
### Adaptive Derivation & Diagnosis Engine for Physics Learning

---

## 📌 Overview

PhysicsMentor AI is an **Agentic AI-powered tutor** designed for B.Tech Physics students who need conceptual clarity beyond classroom hours.

Unlike traditional RAG-based chatbots, this system behaves like a **human tutor** — it detects confusion, adapts explanation difficulty, corrects mistakes, and guides students through step-by-step reasoning.

---

## 🎯 Problem Statement

Students often struggle with:
- Understanding **core physics concepts**
- Memorizing formulas without knowing derivations
- Making **incorrect assumptions or formula mistakes**
- Lack of guidance outside classroom hours  

Most AI tools simply provide answers. They do not adapt, diagnose, or teach.

---

## 🚀 Solution

PhysicsMentor AI introduces an **adaptive teaching system** that:
- Detects when a student is confused  
- Adjusts explanation style dynamically  
- Corrects incorrect formulas  
- Provides step-by-step derivations  
- Maintains conversational memory  

---

## 🔥 Key Features

### 🧠 Confusion Detection Engine
- Identifies phrases like:
  - “I don’t understand”
  - “This doesn’t make sense”
- Switches to **simpler explanations and analogies**
- Asks follow-up questions for clarity  

---

### 📊 Difficulty Adaptation
- Automatically adjusts explanation level:
  - Beginner → simple and intuitive  
  - Intermediate → balanced explanation  
  - Advanced → detailed derivations  

---

### 🧮 Formula Checker Tool
- Detects incorrect formulas (e.g., `KE = mv²`)
- Corrects them (`KE = ½mv²`)
- Explains why the mistake is wrong  

---

### 📐 Step-by-Step Derivation Mode
- Generates:
  - Numbered steps  
  - Intermediate equations  
  - Physical intuition  

---

### 🧠 Multi-turn Memory
- Remembers:
  - Student name  
  - Previous context  
- Enables natural conversation flow  

---

### 📚 RAG-based Knowledge System
- Uses curated physics documents  
- Ensures answers are **grounded and accurate**  

---

## 🏗️ Architecture

Built using **LangGraph StateGraph** with enhanced routing:
User Input
↓
memory_node
↓
router_node
↓
confusion_detector_node
↓
difficulty_adapter_node
↓
(retrieval / tool / derivation)
↓
answer_node
↓
eval_node
↓
save_node → END


**Total Nodes:** 10 (including custom adaptive nodes)

---

## 🛠️ Tech Stack

| Component        | Technology |
|----------------|-----------|
| LLM            | Groq (LLaMA 3.3) |
| Framework      | LangGraph |
| Embeddings     | all-MiniLM-L6-v2 |
| Vector DB      | ChromaDB |
| UI             | Streamlit |
| Evaluation     | RAGAS |

---

## 👤 Author

**Name:** Barsha Patra  
**Roll Number:** 2305530
**Course:** Agentic AI Capstone 2026  
