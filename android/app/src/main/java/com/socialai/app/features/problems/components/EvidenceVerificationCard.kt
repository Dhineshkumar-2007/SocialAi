package com.socialai.app.features.problems.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.socialai.app.core.data.models.EvidenceAnalysis

@Composable
fun EvidenceVerificationCard(evidence: EvidenceAnalysis, serverUrl: String) {
    val statusColor = when (evidence.status.uppercase()) {
        "SUPPORTING" -> Color.Green
        "MANUAL_REVIEW" -> Color(0xFFFFC107) // Amber
        "UNCERTAIN" -> Color(0xFFFF9800) // Orange
        "IRRELEVANT" -> Color.Red
        else -> Color.Gray
    }

    Card(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        border = BorderStroke(2.dp, statusColor)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            AsyncImage(
                model = "$serverUrl/uploads/${evidence.filename}",
                contentDescription = "Evidence Image",
                modifier = Modifier.fillMaxWidth().height(200.dp),
                contentScale = ContentScale.Crop
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = "Status", style = MaterialTheme.typography.titleMedium)
                Badge(containerColor = statusColor) {
                    Text(evidence.status, modifier = Modifier.padding(horizontal = 4.dp), color = Color.White)
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "Caption: ${evidence.caption}", style = MaterialTheme.typography.bodyMedium)
            
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "Relevance Score: ${(evidence.relevanceScore * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
            LinearProgressIndicator(
                progress = { evidence.relevanceScore.toFloat() },
                modifier = Modifier.fillMaxWidth(),
                color = statusColor
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "Reason: ${evidence.reason}", style = MaterialTheme.typography.bodySmall)
        }
    }
}
