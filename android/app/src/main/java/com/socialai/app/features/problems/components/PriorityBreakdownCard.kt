package com.socialai.app.features.problems.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.socialai.app.core.data.models.PriorityResult

@Composable
fun PriorityBreakdownCard(priority: PriorityResult) {
    val color = when (priority.level.uppercase()) {
        "CRITICAL" -> Color.Red
        "HIGH" -> Color(0xFFFF9800)
        "MEDIUM" -> Color.Yellow
        else -> Color.Green
    }
    
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(text = "Priority Level: ", style = MaterialTheme.typography.titleLarge)
                Text(text = priority.level, color = color, style = MaterialTheme.typography.titleLarge)
            }
            Text(text = "Score: ${priority.score}", style = MaterialTheme.typography.displayMedium)
            
            Spacer(modifier = Modifier.height(16.dp))
            
            PriorityComponent("Severity (×0.35)", priority.severityScore)
            PriorityComponent("Population Impact (×0.20)", priority.populationImpactScore)
            PriorityComponent("Evidence Quality (×0.20)", priority.evidenceQualityScore)
            PriorityComponent("Duplicate Reports (×0.10)", priority.duplicateScore)
            PriorityComponent("Safety Risk (×0.15)", priority.safetyRiskScore)
            
            Spacer(modifier = Modifier.height(16.dp))
            Text(text = "Formula: (Sev×0.35) + (Pop×0.20) + (Evd×0.20) + (Dup×0.10) + (Safe×0.15)", style = MaterialTheme.typography.labelSmall)
            
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                CircularProgressIndicator(
                    progress = { (priority.score / 100f).toFloat() },
                    color = color,
                    modifier = Modifier.size(64.dp)
                )
            }
        }
    }
}

@Composable
private fun PriorityComponent(label: String, score: Double) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(text = label, style = MaterialTheme.typography.bodySmall)
            Text(text = String.format("%.1f", score), style = MaterialTheme.typography.bodySmall)
        }
        LinearProgressIndicator(progress = { (score / 100f).toFloat() }, modifier = Modifier.fillMaxWidth())
    }
}
