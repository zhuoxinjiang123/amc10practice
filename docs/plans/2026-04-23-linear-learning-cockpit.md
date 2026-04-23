# Linear Learning Cockpit Implementation Plan

> **For the coding agent:** Implement this plan task-by-task and verify before publishing.

**Goal:** Improve the AMC 10 practice UI using an awesome-design-md inspired Linear learning cockpit style.

**Architecture:** This is a template/CSS-only redesign with small test coverage for design hooks. Flask routes and persistence remain unchanged.

**Tech Stack:** Flask templates, vanilla CSS, Python unittest.

---

### Task 1: Add Template Regression Tests

**Files:**
- Modify: `tests/test_index_dashboard.py`
- Modify: `tests/test_topic_page.py`
- Modify: `tests/test_question_page.py`

**Steps:**
1. Add assertions for new dashboard hero/card classes.
2. Add assertions for new topic checklist/status classes.
3. Add assertions for upgraded practice timer/action classes.
4. Run the targeted tests and verify they fail before template changes.

### Task 2: Update Templates

**Files:**
- Modify: `templates/index.html`
- Modify: `templates/topic.html`
- Modify: `templates/practice.html`

**Steps:**
1. Add hero, progress summary, and topic progress bars on the dashboard.
2. Add refined topic header, metric cards, status pills, and question row metadata.
3. Add upgraded practice shell hooks around timers, answer actions, and AI panel.

### Task 3: Update Styles

**Files:**
- Modify: `static/style.css`

**Steps:**
1. Replace generic visual tokens with the learning cockpit palette and type scale.
2. Style dashboard/topic/practice surfaces, progress bars, statuses, timers, and responsive states.
3. Keep existing class names where tests and behavior rely on them.

### Task 4: Verify And Publish

**Steps:**
1. Run `python3 -m unittest discover -s tests -p 'test_*.py'`.
2. Run `python3 -m py_compile app.py`.
3. Commit and push to `main` for Render redeploy.
