document.getElementById('searchForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const query = document.getElementById('searchQuery').value;
    searchPhotos(query);
});

document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const photoInput = document.getElementById('photo');
    const customLabelsInput = document.getElementById('customLabels');
    const photo = photoInput.files[0];
    const customLabels = customLabelsInput.value.split(',').map(label => label.trim());
    uploadPhoto(photo, customLabels);
});

document.getElementById('voiceSearchButton').addEventListener('click', function() {
    startVoiceRecognition();
});

let recognition;

// Get the voice search button and attach an event listener
const voiceSearchButton = document.getElementById('voiceSearchButton');
voiceSearchButton.addEventListener('click', startVoiceRecognition);


function startVoiceRecognition() {
    console.log('Starting voice recognition...');
    var recognition = new webkitSpeechRecognition();
    recognition.onresult = function (event) {
        var transcript = event.results[0][0].transcript;
        document.getElementById('searchQuery').value = transcript;
        searchPhotos(transcript);
    };
    recognition.start();
}

function stopVoiceRecognition() {
    if (recognition) {
        recognition.stop();
    }
}

function searchPhotos(query) {
    // Make a fetch request to the /search endpoint
    fetch(`https://cl5eo1i8t5.execute-api.us-east-1.amazonaws.com/test-stage/search?q=${query}`)
        .then(response => response.json())
        .then(results => {
            // Process search results and update the display area
            updateSearchResults(results);
        })
        .catch(error => {
            console.error('Error fetching search results:', error);
        });
}

function uploadPhoto(photo, customLabels) {
    // Create a FormData object to send the photo and custom labels
    // const formData = new FormData();
    // formData.append('photo', photo);
    // formData.append('customLabels', customLabels.join(','));

    console.log('customLabels',customLabels)

    // Make a fetch request to the /upload endpoint
    fetch('https://cl5eo1i8t5.execute-api.us-east-1.amazonaws.com/test-stage/upload/coms6998-asm-2/'+photo.name, {
        method: 'PUT',
        body: photo,
        headers: {
            'x-amz-meta-customlabels': customLabels.join(','),
            // 'accept': 'application/json',
            'Content-Type': photo.type
        }
    })
    
        .then(response => {
            if (!response.ok) {
                throw new Error('Error uploading photo');
            }
            console.log('Photo uploaded successfully');
        })
        .catch(error => {
            console.error('Error uploading photo:', error);
        });
}

function updateSearchResults(results) {
    console.log('Received search results:', results);
    
    const searchResultsContainer = document.getElementById('searchResults');
    // Clear previous results
    searchResultsContainer.innerHTML = '';

    if (results.body && Array.isArray(results.body)) {
        // Display each photo in the search results
        results.body.forEach(photo => {
            const photoElement = document.createElement('div');
            photoElement.classList.add('photo');
            photoElement.innerHTML = `
                <img src="${photo.imageUrl}" alt="${photo.objectKey}">
                <p>Labels: ${photo.labels.join(', ')}</p>
            `;
            searchResultsContainer.appendChild(photoElement);
        });
    } else {
        console.error('Invalid search results format:', results);
    }
}


