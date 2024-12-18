import socket
import json
import threading
import imaplib
import email
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailAutomation:
    def __init__(self, email_address, email_password, 
                 imap_server='imap.gmail.com', 
                 smtp_server='smtp.gmail.com'):
        self.email_address = email_address
        self.email_password = email_password
        self.imap_server = imap_server
        self.smtp_server = smtp_server
        self.imap_port = 993
        self.smtp_port = 587

    def send_email(self, recipient_email, subject, body):
        """
        Send an email using SMTP
        """
        try:
            # Set up the SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)

            # Create the email
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Send the email
            server.sendmail(self.email_address, recipient_email, msg.as_string())
            server.quit()

            return True, "Email sent successfully"
        except Exception as e:
            print(f"SMTP Email sending error: {e}")
            return False, str(e)

    def fetch_recent_emails(self, search_criteria='UNSEEN', limit=5):
        """
        Fetch recent emails using IMAP
        
        :param search_criteria: IMAP search criteria (default: UNSEEN)
        :param limit: Number of recent emails to fetch
        :return: List of email details
        """
        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')

            # Search for emails
            _, search_data = mail.search(None, search_criteria)
            email_ids = search_data[0].split()

            emails = []
            # Fetch last 'limit' emails
            for email_id in email_ids[-limit:]:
                _, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                # Extract email details
                subject = email_message['Subject']
                sender = email_message['From']
                body = self._get_email_body(email_message)

                emails.append({
                    'id': email_id,
                    'subject': subject,
                    'sender': sender,
                    'body': body
                })

            mail.close()
            mail.logout()

            return emails
        except Exception as e:
            print(f"IMAP Email fetching error: {e}")
            return []

    def _get_email_body(self, email_message):
        """
        Extract email body from a multipart email
        """
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = email_message.get_payload(decode=True).decode()
        return body

    def get_recipe_ingredients(self, food_type, api_key):
        """
        Fetch ingredients for a specific food type using Spoonacular API
        """
        url = 'https://api.spoonacular.com/recipes/complexSearch'
        params = {
            'query': food_type,
            'apiKey': api_key,
            'number': 1,
            'addRecipeInformation': True,
            'fillIngredients': True
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if data['results']:
                ingredients = [ingredient['original'] for ingredient in data['results'][0]['extendedIngredients']]
                return ingredients
            else:
                return []
        except Exception as e:
            print(f"API Error: {e}")
            return []

def handle_client_connection(conn):
    """
    Handle individual client connections
    """
    try:
        # Receive data from client
        data = conn.recv(1024)
        if not data:
            return

        # Parse incoming request
        request_data = json.loads(data.decode('utf-8'))
        
        # Check request type
        request_type = request_data.get('type', 'recipe')

        # Initialize email automation
        email_automation = EmailAutomation(
            email_address=os.getenv('EMAIL_ADDRESS'),
            email_password=os.getenv('EMAIL_PASSWORD')
        )

        if request_type == 'recipe':
            # Recipe ingredients request
            food_type = request_data.get('food_type')
            recipient_email = request_data.get('recipient_email')

            # Get ingredients
            ingredients = email_automation.get_recipe_ingredients(
                food_type, 
                os.getenv('SPOONACULAR_API_KEY')
            )

            if ingredients:
                # Prepare email
                ingredients_list = '\n'.join(ingredients)
                subject = f"Ingredients for {food_type} Recipe"
                body = f"Here are the ingredients for your {food_type} recipe:\n\n{ingredients_list}"

                # Send email
                success, message = email_automation.send_email(recipient_email, subject, body)

                # Prepare response
                response = {
                    'success': success,
                    'message': message,
                    'ingredients': ingredients
                }
            else:
                # No ingredients found
                response = {
                    'success': False,
                    'message': "No ingredients found",
                    'ingredients': []
                }
        

        elif request_type == 'fetch_emails':
            # Fetch recent emails request
            emails = email_automation.fetch_recent_emails()
            response = {
                'success': True,
                'emails': emails
            }

        else:
            response = {
                'success': False,
                'message': 'Invalid request type'
            }

        # Send response back to client
        conn.sendall(json.dumps(response).encode('utf-8'))

    except Exception as e:
        print(f"Error handling client connection: {e}")
        # Send error response
        conn.sendall(json.dumps({
            'success': False,
            'message': str(e)
        }).encode('utf-8'))
    finally:
        conn.close()

def start_server(host='127.0.0.1', port=65432):
    """
    Start the TCP socket server
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Server listening on {host}:{port}")

        while True:
            # Accept client connections
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")

            # Handle each connection in a new thread
            client_thread = threading.Thread(target=handle_client_connection, args=(conn,))
            client_thread.start()

if __name__ == '__main__':
    start_server()