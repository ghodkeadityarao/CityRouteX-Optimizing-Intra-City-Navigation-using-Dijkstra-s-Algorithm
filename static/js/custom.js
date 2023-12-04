// to get current year
function getYear() {
    var currentDate = new Date();
    var currentYear = currentDate.getFullYear();
    document.querySelector("#displayYear").innerHTML = currentYear;
}

getYear();

//service section owl carousel
$(".service_owl-carousel").owlCarousel({
    autoplay: true,
    center: true,
    nav: true,
    loop: true,
    margin: 0,
    responsive: {
        0: {
            items: 1
        },
        768: {
            items: 3,
        },
        991: {
            items: 3
        }
    }
});

// owl carousel slider js
var owl = $('.portfolio_carousel').owlCarousel({
    loop: true,
    margin: 15,
    dots: false,
    center: true,
    autoplay: true,
    navText: [
        '<i class="fa fa-arrow-left" aria-hidden="true"></i>',
        '<i class="fa fa-arrow-right" aria-hidden="true"></i>'
    ],
    autoplayHoverPause: true,
    responsive: {
        0: {
            center: false,
            items: 1,
            margin: 0
        },
        576: {
            items: 2
        },
        991: {
            center: true,
            items: 3
        }
    }
})


// owl.owlcarousel2_filter

$('.owl-filter-bar').on('click', '.item', function (e) {
    var $items = $('.owl-filter-bar a')
    var $item = $(this);
    var filter = $item.data('owl-filter')
    $items.removeClass("active");
    $item.addClass("active");
    owl.owlcarousel2_filter(filter);

    e.preventDefault();
})
/** google_map js **/
function myMap() {
    var mapProp = {
        center: new google.maps.LatLng(40.712775, -74.005973),
        zoom: 18,
    };
    var map = new google.maps.Map(document.getElementById("googleMap"), mapProp);
}

// nice select
$(document).ready(function () {
    $('select').niceSelect();
});


// An array of words that the autocomplete feature will match against
var search_terms = ['Yamuna Bank', 'Laxmi Nagar', 'Nirman Vihar', 'Preet Vihar', 'Karkarduma', 'Anand Vihar', 'Kaushambi', 'Vaishali', 'Dwarka Sector 21', 'Dwarka Sector 8', 'Dwarka Sector 9', 'Dwarka Sector 10', 'Dwarka Sector 11', 'Dwarka Sector 12', 'Dwarka Sector 13', 'Dwarka Sector 14', 'Dwarka', 'Dwarka Mor', 'Uttam Nagar West', 'Uttam Nagar East', 'Janakpuri West', 'Janakpuri East', 'Tilak Nagar', 'Subhash Nagar', 'Tagore Garden', 'Rajouri Garden', 'Ramesh Nagar', 'Moti Nagar', 'Kirti Nagar', 'Shadipur', 'Patel Nagar', 'Rajendra Place', 'Karol Bagh', 'Jhandewalan', 'Ramakrishna Ashram Marg', 'Rajiv Chowk', 'Barakhambha Road', 'Mandi House', 'Supreme Court', 'Indraprastha', 'Akshardham', 'Mayur Vihar I', 'Mayur Vihar Extension', 'New Ashok Nagar', 'Noida Sector 15', 'Noida Sector 16', 'Noida Sector 18', 'Botanical Garden', 'Golf Course', 'Noida City Centre', 'Noida Sector 34', 'Noida Sector 52', 'Noida Sector 61', 'Noida Sector 59', 'Noida Sector 62', 'Noida Electronic City', 'Inderlok', 'Ashok Park Main', 'Satguru Ramsingh Marg', 'Brigadier Hoshiyar Singh', 'Bahadurgarh City', 'Pandit Shree Ram Sharma', 'Tikri Border', 'Tikri Kalan', 'Ghevra', 'Mundka Industrial Area', 'Mundka', 'Rajdhani Park', 'Nangloi Railway station', 'Nangloi', 'Maharaja Surajmal Stadium', 'Udyog Nagar', 'Peera Garhi', 'Paschim Vihar West', 'Paschim Vihar East', 'Madipur', 'Shivaji Park', 'Punjabi Bagh', 'Nangli', 'Najafgarh','Dhasa Bus stand', 'Okhla Bird Sanctuary', 'Kalindi Kunj', 'Jasola Vihar Shaheen Bagh', 'Okhla Vihar', 'Jamia Millia Islamia', 'Sukhdev Vihar', 'Okhla NSIC', 'Kalkaji Mandir', 'Nehru Enclave', 'Greater Kailash', 'Chirag Delhi', 'Panchsheel Park', 'Hauz Khas', 'IIT', 'R.K.Puram', 'Munirka', 'Vasant Vihar', 'Shankar Vihar', 'Terminal 1-IGI Airport', 'Sadar Bazaar Cantonment', 'Palam', 'Dashrath Puri', 'Dabri Mor-Janakpuri South', 'New Delhi', 'Shivaji Stadium', 'Dhaula Kuan', 'Delhi Aerocity', 'IGI Airport', 'Majlis Park', 'Shalimar Bagh', 'Netaji Subhash Place', 'Shakurpur', 'Punjabi Bagh West', 'ESI Hospital', 'Mayapuri', 'Naraina Vihar', 'Delhi Cantonment', 'Durgabai Deshmukh South Campus', 'Sir Vishweshwaraiah Moti Bagh', 'Bhikaji Cama Place', 'Sarojini Nagar', 'INA', 'South Extension', 'Lajpat Nagar', 'Vinobapuri', 'Ashram', 'Sarai Kale Khan', 'Mayur Vihar Pocket I', 'Trilokpuri Sanjay Lake', 'East Vinod Nagar Mayur Vihar-II', 'Mandawali West Vinod Nagar', 'IP Extension', 'Karkarduma Court', 'Krishna Nagar', 'East Azad Nagar', 'Welcome', 'Jaffrabad', 'Maujpur-Babarpur', 'Gokulpuri', 'Johari Enclave', 'Shiv Vihar', 'Shaheed Sthal', 'Hindon', 'Arthala', 'Mohan Nagar', 'Shyam Park', 'Major Mohit Sharma', 'Raj Bagh', 'Shaheed Nagar', 'Dilshad Garden', 'Jhilmil', 'Mansarovar Park', 'Shahdara', 'Seelampur', 'Shastri Park', 'Kashmere Gate', 'Tis Hazari', 'Pul Bangash', 'Pratap Nagar', 'Shastri Nagar', 'Kanhaiya Nagar', 'Keshav Puram', 'Kohat Enclave', 'Pitam Pura', 'Rohini East', 'Rohini West', 'Rithala', 'Raja Nahar Singh', 'Sant Surdas (Sihi)', 'Escorts Mujesar', 'Bata Chowk', 'Neelam Chowk Ajronda', 'Old Faridabad', 'Badkal Mor', 'Sector 28', 'Mewala Maharajpur', 'NHPC Chowk', 'Sarai', 'Badarpur Border', 'Tughlakabad Station', 'Mohan Estate', 'Sarita Vihar', 'Jasola Apollo', 'Harkesh Nagar Okhla', 'Govind Puri', 'Nehru Place', 'Kailash Colony', 'Moolchand', 'Jangpura', 'Jawaharlal Nehru Stadium', 'Khan Market', 'Central Secretariat', 'Janpath', 'ITO', 'Delhi Gate', 'Jama Masjid', 'Lal Quila', 'Samaypur Badli', 'Rohini Sector 18', 'Haiderpur', 'Jahangirpuri', 'Adarsh Nagar', 'Azadpur', 'Model Town', 'GTB Nagar', 'Vishwa Vidyalaya', 'Vidhan Sabha', 'Civil Lines', 'Chandni Chowk', 'Chawri Bazar', 'Patel Chowk', 'Udyog Bhawan', 'Lok Kalyan Marg', 'Jor Bagh', 'AIIMS', 'Green Park', 'Malviya Nagar', 'Saket', 'Qutab Minar', 'Chhatarpur', 'Sultanpur', 'Ghitorni', 'Arjan Garh', 'Guru Dronacharya', 'Sikandarpur', 'MG Road', 'IFFCO Chowk', 'HUDA City Centre'];

// Function to match the user's input with the search terms
function autocompleteMatch(input) {
  if (input === '') {
    return [];
  }
  var reg = new RegExp(input, "i");
  return search_terms.filter(function(term) {
    return term.match(reg);
  });
}

// Function to show the autocomplete suggestions
function showResults(val, suggestionsId) {
  var suggestions = document.getElementById(suggestionsId);
  suggestions.innerHTML = '';
  let terms = autocompleteMatch(val);
  for (let i=0; i<terms.length; i++) {
    let option = document.createElement("option");
    option.value = terms[i];
    suggestions.appendChild(option);
  }
}


 // User-specified data with game names and colors
 const userGameData = [
    { name: 'Half-Life 2', color: '#FF6347' },
    { name: 'Halo: Combat Evolved', color: '#4682B4' },
    { name: 'Team Fortress 2', color: '#32CD32' },
    { name: 'Tribes', color: '#FFA500' },
    // Add more items as needed
  ];

  const listContainer = document.getElementById('user-colors-list');

  userGameData.forEach((game, index) => {
    const listItem = document.createElement('li');
    listItem.innerHTML = `
      <strong>${game.name}</strong>
      <p>Game description goes here...</p>
    `;
    listItem.style.color = game.color;
    listItem.classList.add(index % 2 === 0 ? 'even' : 'odd');
    listContainer.appendChild(listItem);
  });