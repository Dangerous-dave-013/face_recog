const video = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const imageDataInput = document.getElementById('image_data');

fetch('/stop_feed')
  .then(() => {
    // Now open the webcam
    return navigator.mediaDevices.enumerateDevices();
  })
  .then(devices => {
    const cams = devices.filter(d => d.kind === 'videoinput');
    const realCam = cams.find(d => !d.label.toLowerCase().includes('droid'));

    return navigator.mediaDevices.getUserMedia({
      video: { deviceId: realCam.deviceId }
    });
  })
  .then(stream => {
    document.getElementById('webcam').srcObject = stream;
  })
  .catch(console.error);


// Get access to webcam
navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    video.srcObject = stream;
  })
  .catch(err => {
    console.error("Webcam access failed: ", err);
  });

// Capture image from video
function captureImage() {
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('canvas');
    const imageDataInput = document.getElementById('image_data');

    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg');

    imageDataInput.value = imageData;
    alert("Image Captured!");
}




