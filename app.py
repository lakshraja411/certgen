import os
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


# Function to wrap text into two lines with ellipsis if necessary
def wrap_text_to_two_lines(text, max_line_length=80):
    words = text.split()
    line1, line2 = "", ""

    # First line logic: try to fit words until max_line_length
    for word in words:
        if len(line1) + len(word) + 1 <= max_line_length:
            line1 += (word + " ")
        else:
            break

    # Remaining words go into the second line
    remaining_words = words[len(line1.split()):]
    for word in remaining_words:
        if len(line2) + len(word) + 1 <= max_line_length:
            line2 += (word + " ")
        else:
            break

    # Strip trailing spaces from both lines
    line1 = line1.strip()
    line2 = line2.strip()

    # If line2 exceeds the max length, trim it and add ellipsis
    if len(line2) > max_line_length:
        line2 = line2[:max_line_length - 3] + "..."

    return line1, line2


# Function to create certificates
def create_certificate(
    name, abstract_title, amc_no, template_path, name_y, abstract_y, name_font_size, title_font_size
):
    img = Image.open(template_path)
    draw = ImageDraw.Draw(img)

    # Load fonts
    font_path = r"C:/Users/laksh/Desktop/AMPICON 2024 Certificate/Magnolia.ttf"  # Replace with your font file
    try:
        name_font = ImageFont.truetype(font_path, name_font_size)
        title_font = ImageFont.truetype(font_path, title_font_size)
    except IOError:
        raise IOError("Font file not found. Ensure 'Magnolia.ttf' is in the working directory.")

    # Get the center X-coordinate of the image
    center_x = img.width // 2

    # Add recipient's name at fixed Y-coordinate (616) and centered X
    draw.text((center_x, name_y), name, font=name_font, fill="black", anchor="mm")

    # Wrap abstract title into two lines (with AMC number as part of the title)
    full_title = f"{amc_no}: {abstract_title}"
    line1, line2 = wrap_text_to_two_lines(full_title)

    # Add the abstract title at fixed Y-coordinate (735) and centered X
    draw.text((center_x, abstract_y), line1, font=title_font, fill="black", anchor="mm")
    draw.text((center_x, abstract_y + title_font_size + 10), line2, font=title_font, fill="black", anchor="mm")

    return img


# Function to send email
def send_email(sender_email, sender_password, recipient_email, subject, body, attachment_path):
    try:
        # Create email message
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Add email body
        msg.attach(MIMEText(body, "plain"))

        # Attach certificate
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
        msg.attach(part)

        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False, str(e)


# Streamlit app
def main():
    st.title("Certificate Generator with Email Automation")
    st.write("Upload recipient details, customize placements, preview certificates, and send emails automatically.")

    # Upload Excel File and Certificate Template
    excel_file = st.file_uploader("Upload Recipient Details (Excel File)", type=["xlsx", "xls"])
    template_path = st.file_uploader("Upload Certificate Template (PNG or JPG)", type=["png", "jpg"])

    # Input sender credentials
    st.write("Enter Sender Email Credentials:")
    sender_email = st.text_input("Sender Email")
    sender_password = st.text_input("Sender Password", type="password")

    if excel_file and template_path and sender_email and sender_password:
        # Load recipient details from Excel
        try:
            data = pd.read_excel(excel_file)
            st.write("Preview of Uploaded Data:")
            st.dataframe(data.head())
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            return

        # Check for required columns
        if not {"Name", "Abstract Title", "AMC Number", "Email"}.issubset(data.columns):
            st.error("Excel file must contain columns: 'Name', 'Abstract Title', 'AMC Number', 'Email'")
            return

        # Fixed Y-coordinates for name and abstract title
        name_y = 616
        abstract_y = 735

        # Font size sliders
        st.write("Adjust the font sizes:")
        name_font_size = st.slider("Font Size for Name", 10, 200, 70)
        title_font_size = st.slider("Font Size for Abstract Title", 10, 200, 50)

        # Recipient Selection for Preview
        recipients = data["Name"].tolist()
        selected_recipient = st.selectbox("Select a Recipient for Preview", recipients)

        # Generate Preview
        if st.button("Generate Preview"):
            try:
                recipient_data = data[data["Name"] == selected_recipient].iloc[0]
                preview_img = create_certificate(
                    name=recipient_data["Name"],
                    abstract_title=recipient_data["Abstract Title"],
                    amc_no=recipient_data["AMC Number"],
                    template_path=template_path,
                    name_y=name_y,
                    abstract_y=abstract_y,
                    name_font_size=name_font_size,
                    title_font_size=title_font_size,
                )
                st.image(preview_img, caption="Certificate Preview", use_column_width=True)
            except Exception as e:
                st.error(f"Error generating preview: {e}")

        # Generate All Certificates and Send Emails
        if st.button("Generate and Send Certificates"):
            output_folder = "Generated_Certificates"
            os.makedirs(output_folder, exist_ok=True)

            successes, failures = 0, 0
            for _, row in data.iterrows():
                try:
                    output_path = os.path.join(output_folder, f"{row['Name'].replace(' ', '_')}.pdf")
                    certificate_img = create_certificate(
                        name=row["Name"],
                        abstract_title=row["Abstract Title"],
                        amc_no=row["AMC Number"],
                        template_path=template_path,
                        name_y=name_y,
                        abstract_y=abstract_y,
                        name_font_size=name_font_size,
                        title_font_size=title_font_size,
                    )
                    certificate_img.save(output_path, "PDF")

                    # Send email
                    subject = "Your Certificate of Appreciation"
                    body = f"Dear {row['Name']},\n\nPlease find your certificate attached.\n\nBest regards,\nTeam AMPICON"
                    result = send_email(sender_email, sender_password, row["Email"], subject, body, output_path)
                    if result is True:
                        successes += 1
                    else:
                        failures += 1
                except Exception as e:
                    failures += 1
                    st.error(f"Error processing {row['Name']}: {e}")

            st.success(f"Certificates sent successfully to {successes} recipients!")
            if failures > 0:
                st.warning(f"Failed to send {failures} certificates. Check error logs.")

if __name__ == "__main__":
    main()
