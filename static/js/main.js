// main.js

// Detect if a user is recognized and show the status

// Call this function on page load
window.onload = loadFaceApiModels;
function showRecognitionStatus(status, name) {
    if (status === "recognized") {
        document.getElementById("status").innerHTML = `Entry Approved! Welcome, ${name}`;
        document.getElementById("status").style.color = "green";
    } else {
        document.getElementById("status").innerHTML = "Unauthorized access detected!";
        document.getElementById("status").style.color = "red";
        
        // Call a backend API to send notifications to the admin (Optional)
        fetch('/send-notification', {
            method: 'POST',
            body: JSON.stringify({ message: "Unauthorized access detected!" }),
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
}

// This function will be triggered when the webcam captures the face and gives a result
function onFaceDetected(faceStatus, userName) {
    showRecognitionStatus(faceStatus, userName);
}

let captureButton = document.getElementById('capture');
let canvas = document.getElementById('canvas');
let context = canvas.getContext('2d');

// Start the webcam
navigator.mediaDevices.getUserMedia({ video: true })
  .then((stream) => {
    video.srcObject = stream;
  })
  .catch((err) => {
    console.log('Error accessing webcam: ' + err);
  });

// Capture the image when the button is clicked
captureButton.addEventListener('click', function () {
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Send the image to the server
  let dataURL = canvas.toDataURL('image/jpeg');
  
  // Optional: send the image to the server via AJAX or save to local storage
  console.log('Captured image data:', dataURL);
  
  // Example: send it to a Flask route (adjust the URL based on your route)
  fetch('/register_face', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ image: dataURL }) // or adjust according to your server handling
  })
  .then(response => response.text())
  .then(data => {
    console.log('Success:', data);
  })
  .catch((error) => {
    console.error('Error:', error);
  });
});

let personLoggedIn = false; // Track whether someone is logged in
const video = document.getElementById('webcam');

// Function to start webcam
function startWebcam() {
    navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            const cams = devices.filter(d => d.kind === 'videoinput');
            const realCam = cams.find(d => !d.label.toLowerCase().includes('droid'));

            if (!realCam) {
                alert("No laptop webcam found, only DroidCam?");
                throw new Error("Only DroidCam found");
            }

            return navigator.mediaDevices.getUserMedia({
                video: { deviceId: realCam.deviceId }
            });
        })
        .then(stream => {
            video.srcObject = stream;
            startFaceDetection(stream);
        })
        .catch(err => {
            console.error("Webcam error:", err);
        });
}

// Function to load face-api.js models
async function loadFaceApiModels() {
    await faceapi.nets.ssdMobilenetv1.loadFromUri('/models');
    await faceapi.nets.faceLandmark68Net.loadFromUri('/models');
    await faceapi.nets.faceRecognitionNet.loadFromUri('/models');
    console.log("Models loaded!");
}

// Initialize face-api.js models when the page loads
window.onload = loadFaceApiModels;

// Function to detect faces
async function isPersonInFrame() {
    const detections = await faceapi.detectAllFaces(video).withFaceLandmarks().withFaceDescriptors();

    if (detections.length > 0) {
        console.log('Person detected!');
        return true;
    } else {
        console.log('No person detected');
        return false;
    }
}

// Function to log event
function logEventToServer(name) {
    fetch('/log_event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: name })
    })
    .then(response => response.json())
    .then(data => console.log('Logged event:', data))
    .catch((error) => console.error('Error logging event:', error));
}


// Function to handle person detection in the frame
async function detectPersonInFrame() {
    const personInFrame = await isPersonInFrame();

    if (personInFrame && !personLoggedIn) {
        personLoggedIn = true;
        logEvent("Person detected");
    }

    if (!personInFrame && personLoggedIn) {
        personLoggedIn = false;
    }
}

// Check for person every second
setInterval(detectPersonInFrame, 1000);

// Function to capture image
function captureImage() {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg');

    document.getElementById('image_data').value = imageData;
    console.log("Captured image:", imageData); // Debugging
}

function fetchLogs() {
    fetch('/logs')  // Correct URL to fetch logs from the server
        .then(response => response.json())
        .then(data => {
            const logsContainer = document.getElementById('logs');
            logsContainer.innerHTML = '';  // Clear current logs

            // Populate logs dynamically
            data.forEach(log => {
                const logElement = document.createElement('p');
                logElement.innerText = `${log.name} at ${new Date(log.timestamp * 1000).toLocaleString()}`;
                logsContainer.appendChild(logElement);
            });
        })
        .catch(error => console.error("Error fetching logs:", error));
}

// Refresh logs every 5 seconds
setInterval(fetchLogs, 5000);

// Initial fetch on page load
fetchLogs();

