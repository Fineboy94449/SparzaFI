"""
Generate PDF with SparzaFI Login Credentials
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime

# Create PDF
pdf_filename = "SparzaFI_Login_Credentials.pdf"
doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
story = []

# Styles
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#667eea'),
    spaceAfter=30,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=16,
    textColor=colors.HexColor('#ff7a18'),
    spaceAfter=12,
    spaceBefore=20,
    fontName='Helvetica-Bold'
)

normal_style = ParagraphStyle(
    'CustomNormal',
    parent=styles['Normal'],
    fontSize=11,
    spaceAfter=10,
)

# Title
story.append(Paragraph("🔐 SparzaFI Login Credentials", title_style))
story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
story.append(Spacer(1, 0.3*inch))

# Admin Section
story.append(Paragraph("👨‍💼 Admin Account", heading_style))
admin_data = [
    ['Email:', 'admin@sparzafi.com'],
    ['Password:', 'adminpass'],
    ['Access:', 'Full admin dashboard, user management, verification, analytics']
]
admin_table = Table(admin_data, colWidths=[1.5*inch, 5*inch])
admin_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
]))
story.append(admin_table)
story.append(Spacer(1, 0.2*inch))

# Seller Section
story.append(Paragraph("🏪 Seller Accounts", heading_style))
seller_data = [
    ['Email', 'Password', 'Business Name'],
    ['thandi@sparzafi.com', 'sellerpass', "Thandi's Kitchen (Food)"],
    ['kabelo@sparzafi.com', 'sellerpass', "Kabelo's Crafts (Leather goods)"],
    ['nomsa@sparzafi.com', 'sellerpass', "Nomsa's Beauty Corner (Beauty products)"],
]
seller_table = Table(seller_data, colWidths=[2.2*inch, 1.8*inch, 2.5*inch])
seller_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
]))
story.append(seller_table)
story.append(Spacer(1, 0.2*inch))

# Deliverer Section
story.append(Paragraph("🚚 Deliverer/Driver Accounts", heading_style))
deliverer_data = [
    ['Email', 'Password', 'Vehicle Type'],
    ['sipho.driver@sparzafi.com', 'driverpass', 'Minibus Taxi'],
    ['thembi.driver@sparzafi.com', 'driverpass', 'Motorcycle'],
]
deliverer_table = Table(deliverer_data, colWidths=[2.5*inch, 1.8*inch, 2.2*inch])
deliverer_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff7a18')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fff4e6')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
]))
story.append(deliverer_table)
story.append(Spacer(1, 0.2*inch))

# Buyer Section
story.append(Paragraph("🛒 Buyer Accounts", heading_style))
buyer_data = [
    ['Email', 'Password'],
    ['buyer1@test.com', 'buyerpass'],
    ['buyer2@test.com', 'buyerpass'],
    ['buyer3@test.com', 'buyerpass'],
    ['buyer4@test.com', 'buyerpass'],
]
buyer_table = Table(buyer_data, colWidths=[3*inch, 2*inch])
buyer_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#48bb78')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fff4')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
]))
story.append(buyer_table)
story.append(Spacer(1, 0.3*inch))

# Quick Start Section
story.append(Paragraph("🚀 Quick Start Guide", heading_style))
quickstart_text = """
<b>1. Start the Application:</b><br/>
   cd /home/fineboy94449/Documents/SparzaFI<br/>
   source .venv/bin/activate<br/>
   python3 app.py<br/>
<br/>
<b>2. Access the Platform:</b><br/>
   Open your browser and visit: <b>http://localhost:5000</b><br/>
<br/>
<b>3. Login:</b><br/>
   Use any of the credentials above based on the user type you want to test<br/>
<br/>
<b>4. Features to Test:</b><br/>
   • Admin: User management, verification queue, analytics dashboard<br/>
   • Seller: Product management, sales tracking, seller dashboard<br/>
   • Deliverer: Delivery management, earnings tracking, route management<br/>
   • Buyer: Browse marketplace, add to cart, place orders, track deliveries<br/>
"""
story.append(Paragraph(quickstart_text, normal_style))
story.append(Spacer(1, 0.2*inch))

# Footer
footer_style = ParagraphStyle(
    'Footer',
    parent=styles['Normal'],
    fontSize=9,
    textColor=colors.grey,
    alignment=TA_CENTER,
)
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("SparzaFI - Community Marketplace & Fintech Ecosystem", footer_style))
story.append(Paragraph("All accounts are pre-loaded with SPZ tokens for testing", footer_style))

# Build PDF
doc.build(story)
print(f"✅ PDF created successfully: {pdf_filename}")
