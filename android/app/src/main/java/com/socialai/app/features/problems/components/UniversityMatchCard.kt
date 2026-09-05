package com.socialai.app.features.problems.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.socialai.app.core.data.models.UniversityMatch

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun UniversityMatchCard(match: UniversityMatch, rank: Int) {
    val rankColor = when (rank) {
        1 -> Color(0xFFFFD700) // Gold
        2 -> Color(0xFFC0C0C0) // Silver
        3 -> Color(0xFFCD7F32) // Bronze
        else -> MaterialTheme.colorScheme.primary
    }

    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Badge(containerColor = rankColor) {
                    Text("#$rank", color = Color.Black, modifier = Modifier.padding(4.dp))
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = match.universityName, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Text(text = "${(match.overallScore * 100).toInt()}%", style = MaterialTheme.typography.titleLarge)
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            MatchScoreBar("Semantic Relevance (40%)", match.semanticScore, Color.Blue)
            MatchScoreBar("Faculty Skills (25%)", match.facultyScore, Color.Cyan)
            MatchScoreBar("Lab Capability (15%)", match.labScore, Color.Green)
            MatchScoreBar("Prior Projects (10%)", match.projectScore, Color.Magenta)
            MatchScoreBar("Available Capacity (10%)", match.capacityScore, Color.Red)
            
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "Weights: 40% / 25% / 15% / 10% / 10%", style = MaterialTheme.typography.labelSmall)
            
            Spacer(modifier = Modifier.height(8.dp))
            Text("Required Skills:", style = MaterialTheme.typography.labelMedium)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                match.requiredSkills.forEach { skill ->
                    AssistChip(onClick = {}, label = { Text(skill) })
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = match.explanation, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun MatchScoreBar(label: String, score: Double, color: Color) {
    Column(modifier = Modifier.padding(vertical = 2.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(text = label, style = MaterialTheme.typography.bodySmall)
            Text(text = "${(score * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
        }
        LinearProgressIndicator(
            progress = { score.toFloat() },
            modifier = Modifier.fillMaxWidth(),
            color = color
        )
    }
}
