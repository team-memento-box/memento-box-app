# 사용 예시
from services.text_analyzer import *

# 사용 예시
if __name__ == "__main__":

    print("\n=== Getting all user response texts ===")
    all_texts = get_all_user_response_texts()
    print("All user response texts:", all_texts)
    