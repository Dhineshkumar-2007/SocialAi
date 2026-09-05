package com.socialai.app.features.problems.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.socialai.app.core.data.models.IndustryMatch

@Composable
fun IndustryMatchCard(match: IndustryMatch) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = match.industryName, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Badge(containerColor = MaterialTheme.colorScheme.secondaryContainer) {
                    Text(match.sector, modifier = Modifier.padding(4.dp))
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = "${(match.overallScore * 100).toInt()}%", style = MaterialTheme.typography.titleLarge)
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Column(modifier = Modifier.padding(vertical = 2.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(text = "Semantic (50%)", style = MaterialTheme.typography.bodySmall)
                    Text(text = "${(match.semanticScore * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                }
                LinearProgressIndicator(progress = { match.semanticScore.toFloat() }, modifier = Modifier.fillMaxWidth())
            }
            
            Column(modifier = Modifier.padding(vertical = 2.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(text = "Skills (25%)", style = MaterialTheme.typography.bodySmall)
                    Text(text = "${(match.skillsScore * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                }
                LinearProgressIndicator(progress = { match.skillsScore.toFloat() }, modifier = Modifier.fillMaxWidth())
            }
            
            Column(modifier = Modifier.padding(vertical = 2.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(text = "Sector (25%)", style = MaterialTheme.typography.bodySmall)
                    Text(text = "${(match.sectorScore * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                }
                LinearProgressIndicator(progress = { match.sectorScore.toFloat() }, modifier = Modifier.fillMaxWidth())
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = match.explanation, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
