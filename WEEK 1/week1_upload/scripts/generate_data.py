"""Generate the KGIT helpdesk dataset (ASSUMED categories - confirm with mentor).

Writes to data/kgit/:
  tickets.csv        50 hand-written TEST tickets (10 per category) with labels
  faqs.csv           30 FAQs (6 per category)
  train_tickets.csv  300 template-generated TRAINING tickets (different wording)
  rag_eval.csv       expected FAQ / NONE / ESCALATE per test ticket

All content is synthetic. Run:  python scripts/generate_data.py
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(11)
OUT = Path(__file__).resolve().parents[1] / "data" / "kgit"
OUT.mkdir(parents=True, exist_ok=True)

TEAMS = {
    "IT Support": "IT Service Desk",
    "Access & Accounts": "Identity & Access Team",
    "Training & Courses": "Learning Team",
    "HR & Admin": "HR & Admin Team",
    "Billing & Finance": "Finance Team",
}

# (subject, body, category, priority, escalate, expected RAG outcome)
TICKETS = [
    # ---------------- IT Support ----------------
    ("VPN down for whole team", "VPN is not connecting for the entire team since 9 AM. Nobody can access the client servers.", "IT Support", "Critical", "Yes", "FAQ-001"),
    ("Laptop very slow", "My office laptop takes 10 minutes to start and every application is very slow.", "IT Support", "Medium", "No", "FAQ-002"),
    ("Outlook not syncing", "Outlook is not syncing new emails since yesterday. I can only see old mails.", "IT Support", "Medium", "No", "FAQ-003"),
    ("Install VS Code and Python", "Please install VS Code and Python 3.11 on my laptop for the new project.", "IT Support", "Low", "No", "FAQ-004"),
    ("Printer not working", "The printer on the 2nd floor shows offline and is not printing.", "IT Support", "Low", "No", "FAQ-005"),
    ("Clicked a suspicious link", "I clicked a link in a phishing email asking for my password. I am worried my laptop is infected.", "IT Support", "Critical", "Yes", "ESCALATE"),
    ("Wi-Fi keeps disconnecting", "The Wi-Fi in training lab 3 keeps disconnecting every few minutes during sessions.", "IT Support", "Medium", "No", "FAQ-006"),
    ("Laptop blue screen", "My laptop crashes with a blue screen every 10 minutes. I have a client demo today and cannot work.", "IT Support", "High", "No", "NONE"),
    ("Need a second monitor", "Can I get an extra monitor for my desk? It will help with coding work.", "IT Support", "Low", "No", "NONE"),
    ("Project files missing", "All project files are missing from the shared drive folder. I cannot continue my work.", "IT Support", "High", "No", "NONE"),
    # ---------------- Access & Accounts ----------------
    ("Forgot LMS password", "I forgot my LMS portal password and the reset mail is not coming.", "Access & Accounts", "Medium", "No", "FAQ-007"),
    ("Account locked", "My account got locked after entering the wrong password 3 times. Please unlock.", "Access & Accounts", "Medium", "No", "FAQ-008"),
    ("GitHub repository access", "Please give me access to the company GitHub organisation for the Helix project repo.", "Access & Accounts", "Low", "No", "FAQ-009"),
    ("New joiner access", "A new intern joins on Monday. Please create her email, LMS and laptop login.", "Access & Accounts", "Medium", "No", "FAQ-010"),
    ("Lost phone with authenticator", "I lost my phone and cannot get the MFA code, so I cannot log in to any system.", "Access & Accounts", "High", "No", "FAQ-011"),
    ("Unknown login on my account", "I got an alert of a login to my account from another country. I did not do this.", "Access & Accounts", "Critical", "Yes", "ESCALATE"),
    ("Remove access for leaver", "An employee left today. Please remove his access to email, VPN and GitHub immediately.", "Access & Accounts", "High", "No", "NONE"),
    ("Jira access request", "I need Jira access to update my project tasks.", "Access & Accounts", "Low", "No", "FAQ-009"),
    ("Password expired", "My password expired and now I cannot log in to the VPN from home.", "Access & Accounts", "High", "No", "FAQ-012"),
    ("Delete my data", "I completed my training last year. Please delete my account and all my personal data.", "Access & Accounts", "High", "Yes", "ESCALATE"),
    # ---------------- Training & Courses ----------------
    ("Course video not loading", "Module 4 videos in the LMS are not loading, it keeps buffering.", "Training & Courses", "Medium", "No", "FAQ-013"),
    ("Certificate not received", "I completed the Data Science course 2 weeks ago but have not received my certificate.", "Training & Courses", "Medium", "No", "FAQ-014"),
    ("Change batch timing", "Can I move from the morning batch to the evening batch?", "Training & Courses", "Low", "No", "FAQ-015"),
    ("Exam portal not opening", "The assessment portal is not opening and my exam starts in 1 hour.", "Training & Courses", "High", "No", "FAQ-018"),
    ("Need course slides", "Please share the slides for last week's Machine Learning session.", "Training & Courses", "Low", "No", "NONE"),
    ("Trainer did not come", "The trainer did not come for today's session and the whole batch has been waiting for an hour.", "Training & Courses", "High", "No", "NONE"),
    ("Marks shown wrong", "My assessment marks are shown as 45 but I scored 72 in the answer review.", "Training & Courses", "Medium", "No", "NONE"),
    ("How to enroll", "How can I enroll for the Python Full Stack course?", "Training & Courses", "Low", "No", "FAQ-016"),
    ("Session recording missing", "The recording of yesterday's live session is missing from the LMS.", "Training & Courses", "Medium", "No", "FAQ-017"),
    ("Complaint about trainer", "The trainer was rude and insulted students in class. This is unacceptable.", "Training & Courses", "Medium", "Yes", "NONE"),
    # ---------------- HR & Admin ----------------
    ("Salary not credited", "My salary has not been credited this month. Today is the 5th.", "HR & Admin", "High", "No", "FAQ-019"),
    ("Leave not approved", "My leave request for next Friday is still pending in the HR portal.", "HR & Admin", "Medium", "No", "FAQ-020"),
    ("Experience letter", "I need an experience letter for my visa application.", "HR & Admin", "Low", "No", "FAQ-021"),
    ("Lost ID card", "I lost my office ID card. How do I get a new one?", "HR & Admin", "Low", "No", "FAQ-022"),
    ("Payslip download error", "I get an error when I try to download my October payslip.", "HR & Admin", "Medium", "No", "FAQ-023"),
    ("AC not working", "The AC in training room 2 is not cooling.", "HR & Admin", "Low", "No", "NONE"),
    ("Harassment complaint", "I want to report harassment by a colleague. Please treat this confidentially.", "HR & Admin", "High", "Yes", "ESCALATE"),
    ("Update bank details", "I changed my bank. How do I update my account for salary credit?", "HR & Admin", "Low", "No", "NONE"),
    ("Reimbursement pending", "My travel reimbursement claim has been pending for 2 months.", "HR & Admin", "Medium", "No", "FAQ-024"),
    ("Holiday list", "Where can I find the holiday list for 2027?", "HR & Admin", "Low", "No", "NONE"),
    # ---------------- Billing & Finance ----------------
    ("Course fee paid twice", "I was charged twice for the course fee. Please refund one payment.", "Billing & Finance", "High", "No", "FAQ-026"),
    ("Need fee receipt", "Please send the fee receipt with GST details for my course payment.", "Billing & Finance", "Low", "No", "FAQ-025"),
    ("Payment failed, money deducted", "Payment failed on the portal but 25,000 was deducted from my account.", "Billing & Finance", "High", "No", "FAQ-027"),
    ("Refund for cancelled course", "I cancelled my course enrollment 10 days ago but the refund has not come.", "Billing & Finance", "Medium", "No", "FAQ-028"),
    ("Wrong invoice for client", "The invoice for our project shows 3 developers but only 2 were assigned. Please correct it.", "Billing & Finance", "Medium", "No", "NONE"),
    ("EMI option", "Is there an EMI option for the 6-month course fee?", "Billing & Finance", "Low", "No", "FAQ-029"),
    ("Legal notice on invoice", "If the disputed invoice is not cancelled this week we will send a legal notice.", "Billing & Finance", "Critical", "Yes", "ESCALATE"),
    ("Unknown charge", "There is a charge from KGIT on my card that I do not recognise. Is this fraud?", "Billing & Finance", "Critical", "Yes", "ESCALATE"),
    ("Change billing address", "Please change the billing address on our company invoices.", "Billing & Finance", "Low", "No", "FAQ-030"),
    ("Vendor payment pending", "Our vendor payment for September is still pending. Please update the status.", "Billing & Finance", "Medium", "No", "NONE"),
]

FAQS = [
    ("IT Support", "VPN is not connecting. What should I do?", "Restart the VPN client, check your internet, and make sure your password has not expired. If the VPN is down for many users, the IT Service Desk will post an update on the status page."),
    ("IT Support", "My laptop is very slow.", "Restart the laptop, close unused applications and let pending updates finish. If it is still slow, raise a ticket so IT can check the disk and memory."),
    ("IT Support", "Outlook is not syncing emails.", "Check your internet connection, restart Outlook, and use File > Account Settings > Repair. Webmail can be used meanwhile."),
    ("IT Support", "How do I get software installed?", "Request approved software from the Software Center. For software not listed, raise a ticket with the name, version and project need; installation takes 1-2 working days."),
    ("IT Support", "The printer is not working.", "Check that the printer is online and has paper, then remove and re-add it under Settings > Printers. Report hardware faults to the IT Service Desk."),
    ("IT Support", "Wi-Fi keeps disconnecting.", "Forget the network and reconnect using your office login. If the problem is in one room only, report the room number so IT can check the access point."),
    ("Access & Accounts", "How do I reset my LMS or portal password?", "Click 'Forgot Password' on the login page. The reset link is valid for 30 minutes; check your spam folder."),
    ("Access & Accounts", "My account is locked.", "Accounts unlock automatically after 30 minutes, or immediately after a self-service password reset."),
    ("Access & Accounts", "How do I request access to GitHub, Jira or other tools?", "Raise an access request with the tool name and your manager's approval. Access is usually granted within 1 working day."),
    ("Access & Accounts", "How are accounts set up for a new joiner?", "The manager submits the onboarding form at least 3 working days before the joining date. Email, LMS and laptop login are ready on day one."),
    ("Access & Accounts", "I lost the phone with my MFA authenticator.", "Contact the Identity & Access Team with your employee ID. After identity verification, MFA is reset and you can register a new device."),
    ("Access & Accounts", "My password expired.", "Use self-service password reset from the login page or the office network. The new password works on VPN after about 15 minutes."),
    ("Training & Courses", "Course videos are not loading in the LMS.", "Clear the browser cache, try another browser, and check that your internet speed is at least 5 Mbps. Report the module name if one video fails for everyone."),
    ("Training & Courses", "When will I get my course certificate?", "Certificates are issued within 7 working days after all assessments are passed. Download it from LMS > My Certificates."),
    ("Training & Courses", "Can I change my batch timing?", "Batch changes are allowed once per course, subject to seat availability. Request it from LMS > My Courses > Change Batch."),
    ("Training & Courses", "How do I enroll in a course?", "Choose the course on the training portal, select a batch and complete the payment. You get LMS access within 24 hours."),
    ("Training & Courses", "Where can I find session recordings?", "Recordings are uploaded to the course page in the LMS within 24 hours after each live session."),
    ("Training & Courses", "The exam or assessment portal is not opening.", "Use Chrome, clear the cache and disable pop-up blockers. If the portal does not open 15 minutes before the exam, contact your trainer so the exam can be rescheduled."),
    ("HR & Admin", "When is salary credited?", "Salary is credited on the last working day of the month. If it is not received by the 3rd of the next month, raise a ticket with HR."),
    ("HR & Admin", "How do I apply for leave or check its status?", "Apply in the HR portal under Leave. Your manager approves it; pending requests can be followed up with your manager."),
    ("HR & Admin", "How do I get an experience letter?", "Request it in the HR portal under Letters. Letters are issued within 5 working days."),
    ("HR & Admin", "I lost my ID card.", "Report the loss to Admin and apply for a replacement in the HR portal. A replacement card is ready in 3 working days."),
    ("HR & Admin", "I cannot download my payslip.", "Payslips are in HR portal > Payroll > Payslips. Use Chrome and allow pop-ups; payslips are published on the 2nd of each month."),
    ("HR & Admin", "How do I claim reimbursement?", "Submit claims with bills in the HR portal within 30 days. Approved claims are paid with the next salary."),
    ("Billing & Finance", "How do I get a fee receipt or GST invoice?", "Download receipts from the training portal under Payments. Add your GSTIN before payment to get a GST invoice."),
    ("Billing & Finance", "I was charged twice for my fee.", "Duplicate payments are refunded within 5-7 working days after verification. Share both transaction IDs in the ticket."),
    ("Billing & Finance", "Payment failed but money was deducted.", "Failed payments are reversed by the bank within 5-7 working days. Share the transaction ID if it is not reversed."),
    ("Billing & Finance", "When will I get a refund for a cancelled course?", "Refunds for cancellations within the allowed period are processed within 10 working days to the original payment method."),
    ("Billing & Finance", "Is EMI available for course fees?", "EMI is available for courses above 20,000 through partner banks. Select EMI at checkout."),
    ("Billing & Finance", "How do I change the billing address on invoices?", "Update the billing address in the portal under Company Profile. New invoices use the updated address."),
]

# Training templates: different wording from the test tickets above
FILL = {
    "app": ["Teams", "Outlook", "Chrome", "Zoom", "VS Code", "Excel", "Slack"],
    "tool": ["GitHub", "Jira", "Confluence", "AWS console", "Azure portal", "SharePoint"],
    "course": ["Data Science", "Python Full Stack", "Cloud Computing", "Java", "AI/ML", "DevOps"],
    "room": ["lab 1", "lab 2", "conference room", "training hall", "3rd floor"],
    "month": ["September", "October", "November"],
    "amt": ["12,000", "18,500", "25,000", "4,999", "40,000"],
    "days": ["3 days", "a week", "two weeks", "10 days"],
}
TEMPLATES = {
    "IT Support": [
        "{app} keeps crashing on my system", "internet is very slow in the {room}",
        "my laptop is not turning on", "{app} is not opening after the update",
        "keyboard and mouse not working on my desktop", "projector in the {room} is not working",
        "need {app} installed on my laptop", "system is hanging frequently while running {app}",
        "cannot connect to the office network from the {room}", "laptop battery drains very fast",
        "email server is not sending my mails", "screen flickering on my office laptop",
        "antivirus shows an update error on my machine",
        "VPN disconnects every few minutes when working from home", "need a new headset and webcam for calls",
        "remote desktop to the server is not connecting", "the office internet is down on the {room}",
        "requesting a laptop replacement because of hardware issues",
        "my headset microphone is not picked up in {app}", "speakers on my laptop have no sound",
        "{app} calendar is not syncing my meetings", "printer is showing a paper jam error",
        "mouse and keyboard are not responding", "my disk is almost full and the system is lagging",
        "software licence for {app} has expired", "the projector in the {room} shows no signal",
        "webcam is not detected during video calls", "need a new charger for my laptop",
        "blue screen error appears when I start {app}", "{app} update failed with an error code",
    ],
    "Access & Accounts": [
        "please grant me access to {tool}", "my login to {tool} is not working",
        "need permission to the {tool} project space", "my password reset link expired",
        "I am locked out of my account", "please create login for the new trainee",
        "authenticator app is not showing codes", "remove {tool} access for an ex-employee",
        "I need admin rights on {tool}", "single sign on is failing for {tool}",
        "OTP is not coming for login", "my username is wrong in the directory",
        "need shared mailbox access",
        "changed my mobile so the MFA app needs to be set up again", "security code from the authenticator is rejected",
        "please close my old trainee account and remove my details", "access card for the {room} is not working",
        "want to know who has access to our {tool} space",
        "single sign on to {tool} gives an error", "my account shows as disabled",
        "please create a guest login for a visiting consultant", "I need local admin rights on my laptop",
        "reset my {tool} password please", "add me to the project group on {tool}",
        "my login session expires every few minutes on {tool}", "remove my old email alias",
        "my access to {tool} was removed by mistake",
    ],
    "Training & Courses": [
        "{course} module videos are buffering", "where is my {course} certificate",
        "want to shift my {course} batch to weekends", "how to register for {course}",
        "the {course} quiz is not submitting", "recording of the {course} class is not uploaded",
        "need study material for {course}", "assignment deadline extension for {course}",
        "trainer has not uploaded the {course} notes", "my {course} progress is not updating in LMS",
        "when does the next {course} batch start", "I want to know the syllabus of {course}",
        "mock test for {course} is not opening",
        "my {course} grade is calculated incorrectly", "please send the {course} presentation used in class",
        "online exam for {course} shows a blank page", "the {course} instructor missed the scheduled class",
        "feedback about the {course} trainer behaviour",
        "results of the {course} test are not published", "the {course} quiz is not accepting my answers",
        "can I book a doubt clearing session for {course}", "the {course} live class was cancelled",
        "need an extension for the {course} project submission", "lab exercises for {course} are not opening",
        "how many modules are there in {course}", "the {course} trainer speaks too fast, need recordings",
        "certificate for {course} has a spelling mistake", "want to drop the {course} course and join another",
    ],
    "HR & Admin": [
        "{month} salary is not received yet", "need relieving letter", "apply leave for next week",
        "my leave balance is shown wrong", "request for new ID card", "{month} payslip is not visible",
        "travel claim for {month} not approved", "need address proof letter from HR",
        "seating change request to the {room}", "water dispenser in the {room} is empty",
        "PF details are not updated", "when is the next holiday", "need a no objection certificate",
        "fan and lights not working in the {room}", "facilities: chairs are broken in the {room}",
        "want to raise a confidential complaint about a colleague", "expense claim for client visit not paid",
        "need parking pass for the office",
        "need a bonafide certificate from HR", "when will Form 16 be released", "request for salary certificate",
        "lost my access card for the office door", "food quality in the canteen is very poor",
        "desk relocation request to sit with my team", "medical bill reimbursement not processed",
        "my manager is treating me unfairly and I want to talk to HR", "leave encashment query",
        "insurance card not received", "office cleaning is not done in the {room}",
    ],
    "Billing & Finance": [
        "course fee of {amt} paid but not reflected", "need tax invoice for fee payment of {amt}",
        "refund of {amt} not received after {days}", "amount {amt} debited two times",
        "please share invoice for our company", "is there instalment option for fees",
        "payment gateway failed while paying {amt}", "invoice has wrong company name",
        "vendor bill of {amt} pending for {days}", "need statement of account",
        "GST number missing on the invoice", "partial payment option for {amt} course",
        "receipt not generated for {amt} payment",
        "my credit card shows a payment of {amt} to your company that I did not expect",
        "customer invoice dispute for {month} billing", "how do I pay the course fee in instalments",
        "bank statement shows {amt} paid but status is unpaid",
        "any scholarship available for {amt} course fee", "please send the purchase order copy",
        "we received a duplicate invoice for {month}", "payment reminder received although fee is paid",
        "card was charged for {amt} by KGIT which I did not make", "need the fee structure for the course",
        "how do I get a refund for {amt}", "update the PAN details on our invoice", "credit note required for {month} invoice",
    ],
}
PREFIX = ["", "Hi, ", "Hello team, ", "Urgent: ", "Please help - ", "Dear support, "]
SUFFIX = ["", ".", " please check.", " Thanks.", " kindly help.", "!!"]


def fill(t):
    for k, vals in FILL.items():
        while "{" + k + "}" in t:
            t = t.replace("{" + k + "}", random.choice(vals), 1)
    return t


def main():
    start = datetime(2026, 11, 1, 9, 0)
    with open(OUT / "tickets.csv", "w", newline="", encoding="utf-8") as f, \
         open(OUT / "rag_eval.csv", "w", newline="", encoding="utf-8") as g:
        w, e = csv.writer(f), csv.writer(g)
        w.writerow(["ticket_id", "created_at", "channel", "customer_id", "subject", "body",
                    "category", "priority", "assigned_team", "needs_escalation"])
        e.writerow(["ticket_id", "expected"])
        for i, (subj, body, cat, pri, esc, exp) in enumerate(TICKETS, start=1):
            created = start + timedelta(hours=random.randint(0, 24 * 9), minutes=random.randint(0, 59))
            tid = f"TCK-{i:04d}"
            w.writerow([tid, created.strftime("%Y-%m-%d %H:%M"), random.choice(["email", "web_form", "chat"]),
                        f"EMP-{random.randint(1000, 9999)}", subj, body, cat, pri, TEAMS[cat], esc])
            e.writerow([tid, exp])

    with open(OUT / "faqs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["faq_id", "category", "question", "answer", "version", "approved_by"])
        for i, (cat, q, a) in enumerate(FAQS, start=1):
            w.writerow([f"FAQ-{i:03d}", cat, q, a, "v1.0", "pending_mentor_review"])

    rows = []
    for cat, templates in TEMPLATES.items():
        seen = set()
        while len(seen) < 90:
            seen.add(random.choice(PREFIX) + fill(random.choice(templates)) + random.choice(SUFFIX))
        rows += [(t, cat) for t in sorted(seen)]
    random.shuffle(rows)
    with open(OUT / "train_tickets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "category"])
        w.writerows(rows)
    print(f"KGIT: {len(TICKETS)} tickets, {len(FAQS)} FAQs, {len(rows)} training tickets -> {OUT}")


if __name__ == "__main__":
    main()
