from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from fastapi.responses import JSONResponse

app = FastAPI()

# MongoDB Atlas connection
client = MongoClient("mongodb+srv://cic:cic2002@cluster0.quczg.mongodb.net/")
db = client["college_chatbot"]
ug_programmes_collection = db["ug_programmes"]
pg_programmes_collection = db["pg_programmes"]
college_info_collection = db["college_info"]

@app.post("/")
async def dialogflow_webhook(request: dict):
    # Extract intent and parameters
    intent = request["queryResult"]["intent"]["displayName"]
    parameters = request["queryResult"].get("parameters", {})  # Correctly extract parameters
    print("Parameters:", parameters)  # Debugging output

    # Handle "Ask-Me-Random" intent
    if intent == "Random-Ans":
        college_detail_type = parameters.get("collegedetails")  # Get the detail type

        if not college_detail_type:
            return {
                "fulfillmentText": "What college details would you like to know? "
                                   "For example, library, hostel, transport, or laboratories."
            }

        # Query the collection for the requested type
        detail = college_info_collection.find_one({"type": college_detail_type.lower()})

        if detail:
            # Convert the `details` object to a readable string
            details_string = ""
            if isinstance(detail["details"], dict):
                # Format key-value pairs into a readable string
                details_string = "\n".join(
                    [f"{key}: {value}" for key, value in detail["details"].items()]
                )
            else:
                # If `details` is already a string
                details_string = detail["details"]

            # Return the response to Dialogflow
            return {
                "fulfillmentText": f"Here are the details for {college_detail_type.capitalize()}:\n{details_string}"
            }
        else:
            # Handle case where the detail type isn't found
            return {
                "fulfillmentText": f"Sorry, I couldn't find details about {college_detail_type}. "
                                   "Please check the type and try again."
            }
        program_name = parameters.get("courses")  # Extract course name from parameters
        # Handle if 'courses' is a list
        if isinstance(program_name, list) and len(program_name) > 0:
            program_name = program_name[0]  # Take the first value in the list

        if not program_name:
            return {
                "fulfillmentText": "What course details do you want? Please specify. "
                                   f"Received parameters: {parameters}"
            }

        # Check UG and PG programmes collections
        course_details = ug_programmes_collection.find_one({"program_name": program_name})
        if not course_details:
            course_details = pg_programmes_collection.find_one({"program_name": program_name})

        if course_details:
            response = (
                f"Course Name: {course_details['program_name']}\n"
                f"Duration: {course_details['duration']}\n"
                f"Fees: {course_details['fees_details']}\n"
                f"Staff: {course_details['staff_details']}\n"
                f"Syllabus: {course_details['syllabus']}\n"
                f"Placements: {course_details['placements']}\n\n"
                "Do you have any other queries?"
            )
            return {"fulfillmentText": response}
        else:
            return {
                "fulfillmentText": f"Sorry, I couldn't find details for the course '{program_name}'. "
                                   f"Please provide a correct course name."
            }

    # Define UG and PG program intent mappings for direct intents
    ug_intents = [
        "BE-Electrical", "B-Tech-Artificial-Intelligence", "BE-Electronics",
        "B-Tech-IT", "BE-ComputerScience", "BE-Mechanical"
    ]
    pg_intents = ["MCA", "MBA", "ME-ComputerScience"]

    # Check for UG program intents
    if intent in ug_intents:
        program_name = intent  # Format intent name for database query
        course_details = ug_programmes_collection.find_one({"program_name": program_name})

    # Check for PG program intents
    elif intent in pg_intents:
        program_name = intent  # PG intents match database program names directly
        course_details = pg_programmes_collection.find_one({"program_name": program_name})

    else:
        return {"fulfillmentText": f"I couldn't process your request {parameters}. Please try again."}

    # Build and return response
    if course_details:
        response = (
            f"Course Name: {course_details['program_name']}\n"
            f"Duration: {course_details['duration']}\n"
            f"Fees: {course_details['fees_details']}\n"
            f"Staff: {course_details['staff_details']}\n"
            f"Syllabus: {course_details['syllabus']}\n"
            f"Placements: {course_details['placements']}\n\n"
            "Do you have any other queries?"
        )
        return {"fulfillmentText": response}
    else:
        return {"fulfillmentText": f"Sorry, I couldn't find details for {program_name} in the database."}

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
