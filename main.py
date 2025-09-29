from flask import Flask, request, jsonify
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf import descriptor_pool, symbol_database
from google.protobuf.internal import builder
import traceback
import emoji

app = Flask(__name__)

key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

_sym_db = symbol_database.Default()
descriptor = descriptor_pool.Default().AddSerializedFile(
    b'\n\ndata.proto\"\xbb\x01\n\x04\x44\x61ta\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05'
    b'\x12\x1e\n\x07\x66ield_5\x18\x05 \x01(\x0b\x32\r.EmptyMessage\x12\x1e\n\x07\x66ield_6'
    b'\x18\x06 \x01(\x0b\x32\r.EmptyMessage\x12\x0f\n\x07\x66ield_8\x18\x08 \x01(\t\x12\x0f\n'
    b'\x07\x66ield_9\x18\t \x01(\x05\x12\x1f\n\x08\x66ield_11\x18\x0b \x01(\x0b\x32\r.'
    b'EmptyMessage\x12\x1f\n\x08\x66ield_12\x18\x0c \x01(\x0b\x32\r.EmptyMessage\"\x0e\n'
    b'\x0c\x45mptyMessageb\x06proto3'
)

globals_ = globals()
builder.BuildMessageAndEnumDescriptors(descriptor, globals_)
builder.BuildTopDescriptorsAndMessages(descriptor, 'data1_pb2', globals_)

Data = _sym_db.GetSymbol('Data')
EmptyMessage = _sym_db.GetSymbol('EmptyMessage')


def get_region_url(region):
    region = region.lower()
    return {
        "ind": "https://client.ind.freefiremobile.com",
        "br": "https://client.us.freefiremobile.com",
        "us": "https://client.us.freefiremobile.com",
        "na": "https://client.us.freefiremobile.com",
        "sac": "https://client.us.freefiremobile.com"
    }.get(region, "https://clientbp.ggblueshark.com")


def contains_invalid_chars(text):
    return any(char in emoji.EMOJI_DATA for char in text)

@app.route('/update_bio', methods=['GET'])
def update_bio():
    access_token = request.args.get("access_token")
    bio = request.args.get("bio")

    if not access_token or not bio:
        return jsonify({"error": "Missing 'access_token' or 'bio' parameter."}), 400

    if contains_invalid_chars(bio):
        return jsonify({
            "status": "failed",
            "message": "Bio contains unsupported emojis. Please use plain text or symbols only."
        }), 400

    # Get JWT
    try:
        jwt_api_url = f"https://0xpwn-access-to-jwt.vercel.app/token?access={access_token}"
        jwt_response = requests.get(jwt_api_url, timeout=10)

        if jwt_response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": "Failed to retrieve JWT",
                "status_code": jwt_response.status_code
            }), 502

        jwt_data = jwt_response.json()
        jwt_token = jwt_data.get("token")
        region = jwt_data.get("server", "ind").lower()

        if not jwt_token:
            return jsonify({"error": "JWT missing in response"}), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Exception while retrieving JWT",
            "details": str(e)
        }), 500

    # Build Protobuf
    try:
        data = Data()
        data.field_2 = 17
        data.field_5.CopyFrom(EmptyMessage())
        data.field_6.CopyFrom(EmptyMessage())
        data.field_8 = bio
        data.field_9 = 1
        data.field_11.CopyFrom(EmptyMessage())
        data.field_12.CopyFrom(EmptyMessage())

        serialized = data.SerializeToString()
        padded = pad(serialized, AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(padded)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to build or encrypt protobuf",
            "details": str(e)
        }), 500

    # Send to Free Fire server
    try:
        post_url = f"{get_region_url(region)}/UpdateSocialBasicInfo"
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {jwt_token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB50",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }

        response = requests.post(post_url, headers=headers, data=encrypted, timeout=10)

        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "region": region,
                "bio": bio,
                "uid": jwt_data.get("player_id"),
                "nickname": jwt_data.get("nickname"),
                "platform": jwt_data.get("platform"),
                "response": response.text
            })
        else:
            return jsonify({
                "status": "failure",
                "http_status": response.status_code,
                "server_response": response.text
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Exception during bio update request",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    app.run(debug=True)

