



class NotificationController:
    def __init__(self):
        pass

    def send_notification(self, title ,message):
        """
        Sends a notification to a user.
        
        :param title: The title of the notification.
        :param message: The message to send in the notification.
        """
        if not message or not title:
            raise ValueError("User ID and message cannot be empty.")
        
        # self.notification_service.send(user_id, message)
        
        print(f"Notification! : {title} : {message}")