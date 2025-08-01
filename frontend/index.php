<?php
session_start();
if (!isset($_SESSION['user'])) {
    header("Location: login.php");
    exit();
}

// Process incoming JSON data if this is a POST request
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    header("Content-Type: application/json");
    
    // Get JSON input
    $json_data = file_get_contents("php://input");
    $data = json_decode($json_data, true);
    
    // Process data
    $response = array(
        "data" => $data
    );
    
    // Return JSON response
    echo json_encode($response);
    exit(); // Stop execution after handling the API request
}

// If not a POST request, continue with regular page content below
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PC Activity Monitor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        h2 {
            color: #333;
        }
        #log-list {
            list-style-type: none;
            padding: 0;
        }
        .pc-entry {
            border: 1px solid #ddd;
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 5px;
        }
        .controls {
            margin-top: 10px;
        }
        button {
            padding: 5px 10px;
            margin-right: 5px;
            cursor: pointer;
        }
        .video-container {
            margin-top: 10px;
            display: none;
            border: 1px solid #ccc;
            padding: 5px;
        }
        .video-feed {
            width: 100%;
            max-width: 800px;
            display: block;
        }
        .active-stream {
            border: 2px solid #4CAF50;
            background-color: #f8f8f8;
        }
        .active {
            color: green;
            font-weight: bold;
        }
        .idle {
            color: orange;
            font-weight: bold;
        }
        #status-message {
            margin-top: 10px;
            padding: 8px;
            border-radius: 4px;
            display: none;
        }
        .success {
            background-color: #dff0d8;
            color: #3c763d;
            border: 1px solid #d6e9c6;
        }
        .error {
            background-color: #f2dede;
            color: #a94442;
            border: 1px solid #ebccd1;
        }
    </style>
</head>
<body>
    <h2>Live PC Activity Monitoring</h2>
    <div style="text-align: right; margin-bottom: 10px;">
        <form action="logout.php" method="post" style="display:inline;">
            <button type="submit">Logout</button>
        </form>
    </div>
    
    <!-- Status message div -->
    <div id="status-message"></div>
    
    <ul id="log-list"></ul>

    <script>
        const ws = new WebSocket("ws://172.16.1.5:8000/ws");
        let aaa = null;
        const pcEntries = {}; // Track unique PC entries
        const rtcConnections = {}; // Track WebRTC connections
        let correctedUrl = null; // Placeholder for corrected URL

        ws.onopen = function() {
            console.log("Connected to WebSocket");
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("Received update:", data);

            data.logs.forEach(log => {
                let entry = pcEntries[log.pc_id];

                if (!entry) {
                    // ✅ Create a new entry for this PC
                    entry = document.createElement("li");
                    entry.id = `pc-${log.pc_id}`;
                    entry.className = "pc-entry";
                    entry.innerHTML = `
                        <div>
                            <strong>PC:</strong> ${log.pc_id} |
                            <strong>Window:</strong> <span id="window-${log.pc_id}">${log.active_window}</span> |
                            <strong>Status:</strong> <span id="status-${log.pc_id}" class="${log.status.toLowerCase()}">${log.status}</span>
                        </div>
                        <div class="controls">
                            <button id="capture-${log.pc_id}" onclick="requestScreenshot('${log.pc_id}')">Capture Screenshot</button>
                            <button onclick="openLatestPNG('${log.pc_id}')">Open Latest PNG</button>
                            <button id="stream-${log.pc_id}" onclick="toggleStream('${log.pc_id}')">Start Live Stream</button>
                        </div>
                        <div id="video-container-${log.pc_id}" class="video-container">
                            <canvas id="video-${log.pc_id}" class="video-feed" width="1600" height="900"></canvas>
                        </div>
                    `;
                    document.getElementById("log-list").appendChild(entry);
                    pcEntries[log.pc_id] = entry;
                } else {
                    // ✅ Update existing entry
                    document.getElementById(`window-${log.pc_id}`).textContent = log.active_window;
                    const statusElement = document.getElementById(`status-${log.pc_id}`);
                    statusElement.textContent = log.status;
                    statusElement.className = log.status.toLowerCase();
                }

                // ✅ Update Screenshot Button (if available)
                const screenshotButton = document.getElementById(`screenshot-${log.pc_id}`);
                if (log.screenshot_url) {
                    screenshotButton.style.display = "inline-block";
                    screenshotButton.setAttribute("onclick", `viewScreenshot('${correctedUrl}')`);
                }
            });
        };
        
        function requestScreenshot(pc_id) {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: "capture_screenshot", pc_id: pc_id }));
                console.log(`📸 Screenshot request sent for PC: ${pc_id}`);
                showStatus(`Screenshot request sent for PC: ${pc_id}`, "success");
            } else {
                showStatus("WebSocket is not connected.", "error");
            }
            aaa = pc_id;
        }
        
        // WebRTC Live Stream Functionality
        function toggleStream(pcId) {
            const streamButton = document.getElementById(`stream-${pcId}`);
            const videoContainer = document.getElementById(`video-container-${pcId}`);
            const pcEntry = document.getElementById(`pc-${pcId}`);
            
            if (streamButton.textContent === "Start Live Stream") {
                // Start streaming
                startStream(pcId);
                streamButton.textContent = "Stop Live Stream";
                videoContainer.style.display = "block";
                pcEntry.classList.add("active-stream");
                showStatus(`Starting live stream for PC: ${pcId}`, "success");
            } else {
                // Stop streaming
                stopStream(pcId);
                streamButton.textContent = "Start Live Stream";
                videoContainer.style.display = "none";
                pcEntry.classList.remove("active-stream");
                showStatus(`Stopped live stream for PC: ${pcId}`, "success");
            }
        }

        function startStream(pcId) {
            // Create WebSocket connection for WebRTC
            const rtcWs = new WebSocket("ws://172.16.1.5:8000/webrtc");
            
            rtcWs.onopen = function() {
                console.log(`WebRTC connection opened for ${pcId}`);
                
                // Register as a viewer for this PC
                rtcWs.send(JSON.stringify({
                    type: "register",
                    pc_id: pcId,
                    client_type: "viewer"
                }));
                
                // Store connection
                rtcConnections[pcId] = rtcWs;
            };
            
            rtcWs.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === "video-frame" && data.pc_id === pcId) {
                    // Display the video frame
                    displayFrame(pcId, data.frame);
                } else if (data.type === "stream-ended" && data.pc_id === pcId) {
                    // Handle stream end
                    showStatus(`Stream from ${pcId} has ended.`, "error");
                    stopStream(pcId);
                    const streamButton = document.getElementById(`stream-${pcId}`);
                    streamButton.textContent = "Start Live Stream";
                    document.getElementById(`video-container-${pcId}`).style.display = "none";
                    document.getElementById(`pc-${pcId}`).classList.remove("active-stream");
                }
            };
            
            rtcWs.onclose = function() {
                console.log(`WebRTC connection closed for ${pcId}`);
                
                // Clean up
                if (rtcConnections[pcId]) {
                    delete rtcConnections[pcId];
                }
            };
        }
        
        function stopStream(pcId) {
            // Send command to stop streaming
            if (rtcConnections[pcId]) {
                rtcConnections[pcId].send(JSON.stringify({
                    type: "viewer-command",
                    command: "stop-stream",
                    pc_id: pcId
                }));
                
                // Close connection
                rtcConnections[pcId].close();
                delete rtcConnections[pcId];
            }
        }
        
        function displayFrame(pcId, frameData) {
            const canvas = document.getElementById(`video-${pcId}`);
            const ctx = canvas.getContext('2d');
            
            // Create an image from the base64 data
            const image = new Image();
            image.onload = function() {
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
            };
            image.src = "data:image/jpeg;base64," + frameData;
        }

        ws.onclose = function() {
            console.log("WebSocket closed. Attempting to reconnect...");
            showStatus("Connection lost. Attempting to reconnect...", "error");
            setTimeout(() => location.reload(), 5000);
        };

        // Clean up WebRTC connections when leaving the page
        window.addEventListener('beforeunload', function() {
            Object.keys(rtcConnections).forEach(pcId => {
                stopStream(pcId);
            });
        });
        
        // Function to show status messages
        function showStatus(message, type) {
            const statusElement = document.getElementById('status-message');
            statusElement.textContent = message;
            statusElement.className = type;
            statusElement.style.display = 'block';
            
            // Auto-hide success messages after 5 seconds
            if (type === "success") {
                setTimeout(() => {
                    statusElement.style.display = 'none';
                }, 5000);
            }
        }
        // Modified openLatestPNG function to work with PC ID
        function openLatestPNG(pcId) {
        // Build folder path based on PC ID if provided
        let folderPath = "/MONITORING%20SYSTEM/backend/screenshots/";
        if (pcId) {
            folderPath += `${pcId}/`;
        }
        
        showStatus("Accessing screenshot directory...", "");
        
        // Fetch the directory listing
        fetch(folderPath)
            .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to access directory (${response.status})`);
            }
            return response.text();
            })
            .then(html => {
            // Create a DOM parser to parse the HTML response
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Find all links to PNG files
            const pngLinks = Array.from(doc.querySelectorAll('a[href$=".png"]'));
            
            if (pngLinks.length === 0) {
                showStatus("No PNG files found in the directory", "error");
                return;
            }
            
            // Get all file details and timestamps
            const pngFiles = [];
            
            // Log the table structure to help debug
            const tableRows = doc.querySelectorAll('tr');
            console.log(`Found ${tableRows.length} rows in directory listing`);
            
            // Process each link to a PNG file
            pngLinks.forEach(link => {
                // Get filename
                const filename = link.textContent.trim();
                
                // Find the parent row that contains all file information
                const row = link.closest('tr');
                if (!row) return;
                
                // Debug: Log the entire row HTML to see its structure
                console.log(`Row for ${filename}:`, row.innerHTML);
                
                // Extract all cells in the row to find date and time information
                const cells = Array.from(row.querySelectorAll('td'));
                cells.forEach((cell, index) => {
                console.log(`Cell ${index} for ${filename}:`, cell.textContent.trim());
                });
                
                // Try different strategies to find the date
                let dateText = '';
                let timeText = '';
                
                // Strategy 1: Look for date in second column (common in Apache)
                if (cells.length > 1) {
                dateText = cells[1].textContent.trim();
                }
                
                // Strategy 2: Look for date in third column (common in Nginx)
                if (cells.length > 2 && !dateText) {
                dateText = cells[2].textContent.trim();
                }
                
                // Strategy 3: Look for a cell that contains a date-like string
                if (!dateText) {
                for (const cell of cells) {
                    const cellText = cell.textContent.trim();
                    // Check if the cell contains date-like patterns
                    if (/\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2}/.test(cellText) || 
                        /[a-zA-Z]{3}\s+\d{1,2}/.test(cellText)) {
                    dateText = cellText;
                    break;
                    }
                }
                }
                
                // Strategy 4: Extract timestamp from the filename if it contains date/time info
                // Format like "screenshot_20250510_153045.png" (YYYYMMdd_HHmmss)
                const timestampMatch = filename.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
                if (timestampMatch) {
                const [_, year, month, day, hour, minute, second] = timestampMatch;
                const extractedDate = new Date(
                    parseInt(year), 
                    parseInt(month) - 1, // JS months are 0-indexed
                    parseInt(day),
                    parseInt(hour),
                    parseInt(minute),
                    parseInt(second)
                );
                
                pngFiles.push({
                    filename,
                    href: link.getAttribute('href'),
                    date: extractedDate,
                    dateString: `${year}-${month}-${day} ${hour}:${minute}:${second} (from filename)`,
                    source: 'filename'
                });
                
                console.log(`Extracted timestamp from filename ${filename}: ${extractedDate.toLocaleString()}`);
                } 
                // If we found a date in the table
                else if (dateText) {
                try {
                    // Create a date object from the found date text
                    const parsedDate = new Date(dateText);
                    
                    pngFiles.push({
                    filename,
                    href: link.getAttribute('href'),
                    date: parsedDate,
                    dateString: dateText,
                    source: 'cell'
                    });
                    
                    console.log(`Parsed date for ${filename}: ${parsedDate.toLocaleString()} from "${dateText}"`);
                } catch (e) {
                    console.warn(`Failed to parse date "${dateText}" for ${filename}:`, e);
                }
                }
                // If all else fails, use file modification time from server
                else {
                // Try to find size and date columns based on common patterns
                let modifiedDate = null;
                
                for (let i = 0; i < cells.length; i++) {
                    const cellText = cells[i].textContent.trim();
                    
                    // If this looks like a date cell
                    if (/\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|[A-Za-z]{3}\s+\d{1,2}/.test(cellText)) {
                    modifiedDate = new Date(cellText);
                    break;
                    }
                }
                
                if (modifiedDate && !isNaN(modifiedDate.getTime())) {
                    pngFiles.push({
                    filename,
                    href: link.getAttribute('href'),
                    date: modifiedDate,
                    dateString: modifiedDate.toLocaleString(),
                    source: 'detected'
                    });
                } else {
                    // As a fallback, just use the current time for comparison
                    // (not ideal but will ensure something is displayed)
                    pngFiles.push({
                    filename,
                    href: link.getAttribute('href'),
                    date: new Date(),
                    dateString: "unknown (using current time)",
                    source: 'fallback'
                    });
                }
                }
            });
            
            if (pngFiles.length === 0) {
                showStatus("No PNG files with parseable timestamps found", "warning");
                return;
            }
            
            // Log all found PNG files with their timestamps for debugging
            console.log("All PNG files with timestamps:");
            pngFiles.forEach(file => {
                console.log(`- ${file.filename}: ${file.dateString} (${file.source})`);
            });
            
            // Sort by date (newest first)
            pngFiles.sort((a, b) => a.date.getTime() - b.date.getTime()); // oldest to newest
            const latestPng = pngFiles[pngFiles.length - 1]; // select the latest (newest)

            
            // Display timestamp information
            showStatus(`Opening latest screenshot: ${latestPng.filename} from ${latestPng.dateString}`, "success");
            
            // Create the full URL to the PNG file
            const latestPngUrl = new URL(latestPng.href, window.location.origin + folderPath).href;
            
            // Open the PNG file in a new tab
            window.open(latestPngUrl, "_blank");
            })
            .catch(error => {
            console.error("Error:", error);
            showStatus(`Error: ${error.message}`, "error");
            });
        }

        // Helper function to show status messages
        function showStatus(message, type) {
        console.log(`Status (${type}): ${message}`);
        // Add your UI status display logic here if needed
        }
    </script>
</body>
</html>