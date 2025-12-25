from alipay_api import AlipayAPI
import requests
import io

def test_chinese_cookie():
    api = AlipayAPI()
    # Chinese in cookie
    try:
        api.update_config("test_cookie=你好")
        print("Update config with Chinese cookie: Success")
    except Exception as e:
        print(f"Update config failed: {e}")

    # Try to make a request (even if it fails with 404/403, we check for encoding error)
    try:
        # Just a dummy request to trigger header encoding
        requests.get("https://www.baidu.com", headers=api.headers)
        print("Request with Chinese cookie: Success (network level)")
    except Exception as e:
        print(f"Request with Chinese cookie failed: {e}")

def test_chinese_filename():
    api = AlipayAPI()
    api.update_config("test_cookie=abc")
    
    # Mock file
    f = io.BytesIO(b"test")
    f.filename = "测试图片.jpg"
    f.mimetype = "image/jpeg"
    f.stream = f # Werkzeug FileStorage has stream attribute, here we mock it
    
    # We need to mock requests.post to avoid actual network call if possible, 
    # but the error happens inside requests.post before network if it's encoding.
    # However, to be sure, we can just let it try (it will fail authentication but that's fine).
    
    print("\nTesting upload with Chinese filename...")
    result = api.upload_image(f)
    print(f"Upload result: {result}")

if __name__ == "__main__":
    test_chinese_cookie()
    test_chinese_filename()
