from flask import Flask,render_template, request, redirect, url_for
from backend import *
app = Flask(__name__)

#variables and lists
userGameData = []
csv_file_path = 'Dataset/cp_metro.csv'
graph = load_graph_from_csv(csv_file_path)

app.config['route'] = None
app.config['start_place'] = None
app.config['end_place'] = None
app.config['time_taken'] = None
app.config['cost_total'] = None
app.config['stops_number'] = None
app.config['switches'] = None
app.config['fin_color'] = []

stationsList = ['Yamuna Bank', 'Laxmi Nagar', 'Nirman Vihar', 'Preet Vihar', 'Karkarduma', 'Anand Vihar', 'Kaushambi', 'Vaishali', 'Dwarka Sector 21', 'Dwarka Sector 8', 'Dwarka Sector 9', 'Dwarka Sector 10', 'Dwarka Sector 11', 'Dwarka Sector 12', 'Dwarka Sector 13', 'Dwarka Sector 14', 'Dwarka', 'Dwarka Mor', 'Uttam Nagar West', 'Uttam Nagar East', 'Janakpuri West', 'Janakpuri East', 'Tilak Nagar', 'Subhash Nagar', 'Tagore Garden', 'Rajouri Garden', 'Ramesh Nagar', 'Moti Nagar', 'Kirti Nagar', 'Shadipur', 'Patel Nagar', 'Rajendra Place', 'Karol Bagh', 'Jhandewalan', 'Ramakrishna Ashram Marg', 'Rajiv Chowk', 'Barakhambha Road', 'Mandi House', 'Supreme Court', 'Indraprastha', 'Akshardham', 'Mayur Vihar I', 'Mayur Vihar Extension', 'New Ashok Nagar', 'Noida Sector 15', 'Noida Sector 16', 'Noida Sector 18', 'Botanical Garden', 'Golf Course', 'Noida City Centre', 'Noida Sector 34', 'Noida Sector 52', 'Noida Sector 61', 'Noida Sector 59', 'Noida Sector 62', 'Noida Electronic City', 'Inderlok', 'Ashok Park Main', 'Satguru Ramsingh Marg', 'Brigadier Hoshiyar Singh', 'Bahadurgarh City', 'Pandit Shree Ram Sharma', 'Tikri Border', 'Tikri Kalan', 'Ghevra', 'Mundka Industrial Area', 'Mundka', 'Rajdhani Park', 'Nangloi Railway station', 'Nangloi', 'Maharaja Surajmal Stadium', 'Udyog Nagar', 'Peera Garhi', 'Paschim Vihar West', 'Paschim Vihar East', 'Madipur', 'Shivaji Park', 'Punjabi Bagh', 'Nangli', 'Najafgarh', 'Dhasa Bus stand', 'Okhla Bird Sanctuary', 'Kalindi Kunj', 'Jasola Vihar Shaheen Bagh', 'Okhla Vihar', 'Jamia Millia Islamia', 'Sukhdev Vihar', 'Okhla NSIC', 'Kalkaji Mandir', 'Nehru Enclave', 'Greater Kailash', 'Chirag Delhi', 'Panchsheel Park', 'Hauz Khas', 'IIT', 'R.K.Puram', 'Munirka', 'Vasant Vihar', 'Shankar Vihar', 'Terminal 1-IGI Airport', 'Sadar Bazaar Cantonment', 'Palam', 'Dashrath Puri', 'Dabri Mor-Janakpuri South', 'New Delhi', 'Shivaji Stadium', 'Dhaula Kuan', 'Delhi Aerocity', 'IGI Airport', 'Majlis Park', 'Shalimar Bagh', 'Netaji Subhash Place', 'Shakurpur', 'Punjabi Bagh West', 'ESI Hospital', 'Mayapuri', 'Naraina Vihar', 'Delhi Cantonment', 'Durgabai Deshmukh South Campus', 'Sir Vishweshwaraiah Moti Bagh', 'Bhikaji Cama Place', 'Sarojini Nagar', 'INA', 'South Extension', 'Lajpat Nagar', 'Vinobapuri', 'Ashram', 'Sarai Kale Khan', 'Mayur Vihar Pocket I', 'Trilokpuri Sanjay Lake', 'East Vinod Nagar Mayur Vihar-II', 'Mandawali West Vinod Nagar', 'IP Extension', 'Karkarduma Court', 'Krishna Nagar', 'East Azad Nagar', 'Welcome', 'Jaffrabad', 'Maujpur-Babarpur', 'Gokulpuri', 'Johari Enclave', 'Shiv Vihar', 'Shaheed Sthal', 'Hindon', 'Arthala', 'Mohan Nagar', 'Shyam Park', 'Major Mohit Sharma', 'Raj Bagh', 'Shaheed Nagar', 'Dilshad Garden', 'Jhilmil', 'Mansarovar Park', 'Shahdara', 'Seelampur', 'Shastri Park', 'Kashmere Gate', 'Tis Hazari', 'Pul Bangash', 'Pratap Nagar', 'Shastri Nagar', 'Kanhaiya Nagar', 'Keshav Puram', 'Kohat Enclave', 'Pitam Pura', 'Rohini East', 'Rohini West', 'Rithala', 'Raja Nahar Singh', 'Sant Surdas (Sihi)', 'Escorts Mujesar', 'Bata Chowk', 'Neelam Chowk Ajronda', 'Old Faridabad', 'Badkal Mor', 'Sector 28', 'Mewala Maharajpur', 'NHPC Chowk', 'Sarai', 'Badarpur Border', 'Tughlakabad Station', 'Mohan Estate', 'Sarita Vihar', 'Jasola Apollo', 'Harkesh Nagar Okhla', 'Govind Puri', 'Nehru Place', 'Kailash Colony', 'Moolchand', 'Jangpura', 'Jawaharlal Nehru Stadium', 'Khan Market', 'Central Secretariat', 'Janpath', 'ITO', 'Delhi Gate', 'Jama Masjid', 'Lal Quila', 'Samaypur Badli', 'Rohini Sector 18', 'Haiderpur', 'Jahangirpuri', 'Adarsh Nagar', 'Azadpur', 'Model Town', 'GTB Nagar', 'Vishwa Vidyalaya', 'Vidhan Sabha', 'Civil Lines', 'Chandni Chowk', 'Chawri Bazar', 'Patel Chowk', 'Udyog Bhawan', 'Lok Kalyan Marg', 'Jor Bagh', 'AIIMS', 'Green Park', 'Malviya Nagar', 'Saket', 'Qutab Minar', 'Chhatarpur', 'Sultanpur', 'Ghitorni', 'Arjan Garh', 'Guru Dronacharya', 'Sikandarpur', 'MG Road', 'IFFCO Chowk', 'HUDA City Centre']
colorsList = ['#0000FF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#FFFFFF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#0000FF', '#FFFFFF', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#008000', '#808080', '#808080', '#808080', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FFFFFF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FFFFFF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FF00FF', '#FFFFFF', '#FFA500', '#FFA500', '#FFA500', '#FFA500', '#FFC0CB', '#FFC0CB', '#FFFFFF', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFFFFF', '#FFC0CB', 'FFFFFF', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFFFFF', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FFC0CB', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FFFFFF', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#FF0000', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#FFFFFF', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#FFFFFF', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#9400D3', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFFFF', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00', '#FFFF00']



@app.route('/', methods=['GET', 'POST'])
def hello_world():  
    if(request.method=="POST"):
        app.config['route'] = None
        app.config['start_place']  = request.form.get('start1')
        app.config['end_place']  = request.form.get('end1')
        app.config['route'] = shortest_route(graph, app.config['start_place'] , app.config['end_place'] )
        return redirect(url_for('resultPage'))
    return render_template('index.html')


@app.route('/res')
def resultPage():
    for station in app.config['route']:
        ind = stationsList.index(station)
        # if colorsList[ind] == "#FFFFFF"
        app.config['fin_color'].append(colorsList[ind])
        
    app.config['stops_number'] = len(app.config['route'])
    count=0
    for sw in app.config['fin_color']:
        if(sw == "#FFFFFF"):
            count = count+1
    app.config['switches'] = count

    for routeplace, colorReq in zip(app.config['route'], app.config['fin_color']):
        data = {}
        data['name'] = routeplace
        data['color'] = colorReq
        userGameData.append(data)
    return render_template("result.html", dd=userGameData, ss=app.config['start_place'], ee=app.config['end_place'], stopsNumber=app.config['stops_number'], switchNumber=app.config['switches'], costtotal=50, timetaken=50)

@app.route('/folium')
def funFoliym():
    return render_template("foliumHtml.html")


if __name__ == "__main__":
    app.run(debug = True,port = 5000) 