import os
import uvicorn
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
