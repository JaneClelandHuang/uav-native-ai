---
title: Syllabus
---

# Syllabus

<p class="lede">CSE 40701 · Section 01 · CRN 20469 · Fall 2026</p>

Native AI Software and Systems Engineering for UAVs prepares students to
engineer complex software-intensive systems in an environment where
generative AI is an integral part of the software engineering process. The
course uses autonomous UAV systems as its primary cyber-physical domain and
combines software architecture, AI-assisted development, runtime analysis,
human interaction, perception, autonomy, testing, and assurance.

Students will work extensively with GPT/Claude and related AI tools
throughout the course. The objective is not simply to use AI to generate
code faster. Students will learn how to use AI to understand unfamiliar
systems, explore designs, generate and critique implementations, analyze
operational evidence, build specialized software-engineering agents, and
evaluate the quality of AI-generated work.

A central principle of the course is:

> **Use AI aggressively — but verify, challenge, understand, and take
> responsibility for the result.**

## Course Description

This course prepares senior-level students to engineer software in an
AI-assisted development environment, with an emphasis on cyber-physical
systems in the UAV domain.

The course has two phases.

### Phase I — Individual Skill Building

During the first half of the semester, students individually develop
capabilities needed to engineer intelligent UAV systems. Topics include UAV
software architecture and infrastructure, multi-UAV coordination,
flight-log analysis, runtime monitoring, GUI programming, computer vision,
and AI-supported onboard reasoning.

Each week also develops a complementary **Native AI software-engineering
skill**, including using AI as a learning partner, AI-assisted programming,
data analysis and diagnosis, UI development, engineering AI-enabled
components, and constructing reasoning pipelines.

### Phase II — Team Physical-AI Project

During the second half of the semester, students work in teams to design,
build, test, and demonstrate a swarm-based Physical AI system addressing a
meaningful disaster-relief problem.

Projects may address any aspect of disaster relief or emergency response,
from mission-level planning and swarm coordination to focused hazards,
finding resources, or delivering medicine.

Every project must implement an operational Physical AI loop:

> **PERCEIVE → REASON → ACT**

The system must perceive meaningful information about its operational
environment, use AI-supported reasoning to determine what should happen
next, and cause an action that changes the physical mission or behavior of
the UAV swarm.

Projects also incorporate visualization, human interaction and oversight,
runtime adaptation, safety guardrails, testing, and engineering evidence.

## Learning Goals

Upon successful completion of this course, you will be able to:

1. **Understand and engineer multi-component UAV software systems**,
   including telemetry, command and control, messaging, simulation,
   networking, perception, and operator-facing applications.
2. **Use generative AI effectively as a software-engineering partner** for
   learning, design, implementation, debugging, analysis, testing, and
   review.
3. **Critically evaluate AI-generated software and engineering artifacts**
   rather than treating AI output as authoritative.
4. **Design software architectures for intelligent cyber-physical
   systems** and reason about component responsibilities, interfaces,
   quality attributes, tradeoffs, and architectural risks.
5. **Use rapid architectural spikes and empirical evidence** to reduce
   uncertainty about consequential design decisions.
6. **Analyze operational UAV data** to reconstruct behavior, diagnose
   anomalies, and distinguish evidence from inference.
7. **Develop runtime monitoring and safety mechanisms** for autonomous UAV
   operations.
8. **Engineer operator-facing visualizations and human-autonomy
   interactions** that support effective supervision of autonomous
   systems.
9. **Integrate perception, AI-supported reasoning, and physical action**
   into a coherent Physical AI system.
10. **Build and evaluate specialized software-engineering agents**,
    including agents that support software testing and verification.
11. **Develop tests and empirical evidence** supporting claims about the
    behavior and quality of an intelligent cyber-physical system.
12. **Explain and defend your engineering decisions and contributions**,
    including where AI was useful, where it failed, and where human
    judgment remained essential.

## Prerequisites

Programming Paradigms or Object Oriented Software Engineering, and
Introduction to AI, or by instructor approval.

## Cannot Have Taken

- CSE 40793

## Registration Restrictions

- Prerequisites: CSE 20312 and 30124 and (CSE 30332 or 40232).
- Enrollment limited to students with a semester level of Junior or
  Senior.
- Enrollment limited to students with a program in Computer Engineering or
  Computer Science.
- Enrollment limited to students in the Main campus.

## Course Structure

The course combines short lectures, demonstrations, hands-on exercises,
individual programming assignments, project studios, team presentations,
and an individual oral project defense.

The first half of the semester emphasizes **individual mastery**. The
second half emphasizes **team-based engineering and integration**.

During project sprint weeks, teams will work together during scheduled
class time. Teams may work in appropriate locations throughout Fitzpatrick
Hall, and the instructor will circulate among teams for design reviews,
demonstrations, debugging discussions, and technical consultation.

## Course Infrastructure and Materials

Students will work with an existing multi-UAV software and simulation
environment rather than building a UAV simulator from scratch.

Course technologies include:

- ArduPilot SITL;
- MAVLink;
- MQTT;
- Docker;
- Python;
- Git and GitHub;
- UAV telemetry and flight logs;
- map-based visualization;
- camera and computer-vision pipelines;
- GPT/Claude and related generative-AI tools.

Additional software and setup instructions will be provided during the
course.

**Required Text/Readings:** Practical readings and technical materials
will be assigned throughout the semester in support of each topic. No
textbook is required. In lieu of a textbook, students will be provided
with Claude Pro and Anthropic credits sufficient for all required
exercises and project work.

## Generative AI Policy

Generative AI is an **expected and integral part of this course**.

Students are encouraged and, for many assignments, required to use tools
such as GPT and Claude for activities including:

- understanding unfamiliar software and architectures;
- brainstorming and exploring alternatives;
- generating and modifying code;
- debugging;
- generating tests;
- analyzing data and logs;
- critiquing requirements and architectures;
- building specialized software-engineering agents;
- preparing technical explanations and documentation.

Permission to use AI does not transfer responsibility to AI.

Students remain responsible for the correctness, safety, quality, and
integrity of everything they submit. You must understand the software and
engineering artifacts you submit and be able to explain, critique, modify,
test, and defend them independently.

Some assessments will therefore explicitly evaluate **individual
understanding of AI-assisted work**. These may include individualized
questions based on submitted assignments and an individual oral defense of
the team project.

Unless an assignment states otherwise, students do not need to avoid AI in
order to demonstrate learning. Instead, the course evaluates whether
students can use AI effectively **while retaining engineering judgment and
individual understanding**.

## Individual Assignments

The first portion of the course consists primarily of individual
assignments. Assignments build progressively toward capabilities that may
later be reused in the team project.

Students will maintain private GitHub repositories for individual
coursework. Detailed requirements and due dates will be provided with each
assignment.

Because extensive AI assistance is permitted, assessment may include
individualized follow-up questions based on each student's submitted
implementation or analysis.

## Team Project

The second half of the course centers on a team project in which students
design and build a swarm-based Physical AI system for disaster relief.

Every project must incorporate:

- a meaningful disaster-relief or emergency-response mission;
- multiple coordinated UAVs;
- the required Perceive → Reason → Act loop (see above);
- AI-supported autonomy;
- visualization;
- meaningful human interaction and oversight;
- runtime adaptation;
- safety constraints and guardrails;
- verification and engineering evidence; and
- Native-AI software-engineering practices.

Teams will maintain an evolving GitHub Pages project website documenting
the engineering story of their system from vision through architecture,
implementation, testing, and final evaluation.

Detailed project requirements and deliverable specifications will be
provided separately.

## Grading

The course is graded on a 1,000-point scale. Assessment progresses from
individual skill-building assignments to team project milestones and
culminates in a final working system, project website, live
demonstration, and individual oral defense.

### Individual Skill-Building Assignments — 400 points

| Deliverable | Points |
|---|---:|
| HW1 — UAV Infrastructure & Architecture | 50 |
| HW2 — Multi-UAV Air Traffic Control | 60 |
| HW3 — Flight-Log Analysis | 55 |
| HW4 — Runtime Monitoring & Fault Injection | 55 |
| HW5 — GUI Programming | 60 |
| HW6 — Computer Vision & Perception | 60 |
| HW7 — Onboard Intelligence / Reasoning Pipeline | 60 |
| **Subtotal** | **400** |

Generative AI use is expected on these assignments. Assignment grades
therefore reflect both the quality of the submitted engineering artifact
and demonstrated individual understanding of that artifact. Students may
be asked individualized questions based on their submitted work and should
be prepared to explain, critique, diagnose, and modify what they submit.

### Team Project Milestones — 250 points

| Deliverable | Points |
|---|---:|
| D1 — Project Vision + Native-AI Use Cases | 40 |
| D2 — Architecture + Architectural Spike | 60 |
| D3 — Working System + Architecture Review | 70 |
| D4 — Testing Agent + Engineering Evidence | 80 |
| **Subtotal** | **250** |

Project milestones are maintained through the team's evolving GitHub Pages
project website and project repository. Milestones emphasize working
software, architectural reasoning, integration, testing, evidence, and
effective technical communication rather than lengthy standalone reports.

### Final Project Assessment — 350 points

| Deliverable | Points |
|---|---:|
| D5 — Final Working System + Live Team Presentation | 150 |
| D5 — Final Project Website / Engineering Evidence | 100 |
| Individual Oral Project Defense | 100 |
| **Subtotal** | **350** |

The final project assessment constitutes 35% of the course grade. It
evaluates three complementary forms of evidence:

- **System and demonstration:** What did the team actually build, and can
  it perform the intended Physical AI mission?
- **Website and engineering evidence:** Can the team explain the system
  and provide convincing evidence supporting its important claims?
- **Individual oral defense:** Does each student understand the system
  they helped build and the engineering decisions, evidence, and
  AI-assisted processes behind it?

The team project grade and individual oral-defense grade are separate.
Strong team performance does not substitute for individual understanding.

### Total

| Category | Points | Course Weight |
|---|---:|---:|
| Individual Skill-Building Assignments | 400 | 40% |
| Team Project Milestones | 250 | 25% |
| Final Project Assessment | 350 | 35% |
| **Total** | **1,000** | **100%** |

## Attendance and Participation

This is a highly interactive, project-oriented course. Many class sessions
involve hands-on exercises, demonstrations, architecture discussions, peer
reviews, team development, and project critiques that cannot be fully
reproduced by reading slides afterward.

Regular attendance and active participation are required. Attendance does
not earn points; however, repeated unexcused absences may result in
deductions from the student's final course point total. Students are not
expected to attend class when ill, and reasonable absences for interviews
or other legitimate commitments can be arranged in advance. Because of the
interactive nature of the course, students are expected to email the
instructor whenever they are unable to attend.

After two unexcused absences, each additional unexcused absence results in
a 10-point deduction from the final course point total.

University-approved absences will be handled according to University
policy.

## Academic Integrity

Students are expected to comply with the Notre Dame Academic Code of
Honor.

The unusual role of AI in this course does not eliminate normal
expectations of academic integrity. Using AI where authorized is not
academic dishonesty; misrepresenting another student's work as your own,
violating assignment-specific collaboration rules, or claiming
understanding or contributions that are not your own is.

For team work, students must accurately represent their individual
contributions and appropriately acknowledge the contributions of
teammates.

## Late Work and Extensions

<div class="callout placeholder">
<p><strong>TBD</strong></p>
<p>Grace period, penalty schedule, and extension request process still
need to be specified.</p>
</div>

Project milestone deadlines are particularly important because later
project activities build directly on earlier deliverables. Teams should
communicate emerging problems early rather than waiting until a deadline.

## Technology Use

Computers and software-development tools are integral to this course and
will be used extensively during class. Students are expected to bring
their laptops to class and to have the software and course infrastructure
needed for the day's activities installed and operational.

All required course software will be installed on students' own laptops.
Initial setup will take place during Week 1. If you encounter problems
that prevent the required software or infrastructure from running
successfully on your laptop, notify the instructor during Week 1 so that
we can diagnose the problem and, if necessary, discuss alternative
arrangements.

Software development inevitably involves technical and infrastructure
failures. Students are expected to manage their work accordingly by
committing and pushing changes regularly, maintaining appropriate
backups, and beginning assignments sufficiently early to identify and
resolve technical problems before deadlines.

## Privacy and Course Materials

Course materials are intended for use by students enrolled in this
course. Do not redistribute course materials outside the course without
permission.

Individual student repositories will be private. Team project
repositories will also be private and accessible only to the team,
instructor, and other authorized course personnel.

As part of team formation, each team will discuss and agree upon how it
wishes to share its project website and software. Teams may choose to
keep their project materials private, make the project website publicly
accessible during or after the semester, or create a separate public
version of the project on their own GitHub or personal websites after the
course concludes.

Public release of the project website or software is not required for the
course. Any decision to make team-created materials public should be
agreed upon by all team members. Teams should also consider whether
source code, project data, or other artifacts are appropriate for public
release before publishing or cloning course materials outside the private
team repository.

## Accessibility and Accommodations

It is the policy and practice of the University of Notre Dame to provide
reasonable accommodations for students with properly documented
disabilities. Students who have questions about Sara Bea Accessibility
Services, or who have or think they may have a disability, are encouraged
to contact Sara Bea Accessibility Services as early as possible so that
appropriate accommodations can be arranged.

## Communication & Office Hours

<div class="callout placeholder">
<p><strong>TBD</strong></p>
<p>[Instructor contact info, office hours (time/location/link), expected
response time for messages, preferred channel (email vs. course
forum/Slack/etc.).]</p>
</div>

## Changes to the Syllabus

This course includes emerging technologies and an open-ended project, so
some details of assignments, tools, project activities, and the weekly
schedule may evolve during the semester. Significant changes to
requirements or deadlines will be communicated clearly to the class. The
overall grading structure and point distribution specified in this
syllabus will remain unchanged.
