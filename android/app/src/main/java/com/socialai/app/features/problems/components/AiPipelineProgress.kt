package com.socialai.app.features.problems.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun AiPipelineProgress(timings: Map<String, Double>, isAnalyzing: Boolean) {
    val stages = listOf("Embedding", "Classification", "Skills", "Evidence", "Duplicates", "Priority", "Matching")
    
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Brush.horizontalGradient(listOf(MaterialTheme.colorScheme.primary, MaterialTheme.colorScheme.secondary)))
                    .padding(8.dp)
            ) {
                Text("AI Analysis Pipeline", color = Color.White, style = MaterialTheme.typography.titleMedium)
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            stages.forEach { stage ->
                val time = timings[stage]
                val status = when {
                    time != null -> "✅"
                    isAnalyzing -> "🔄"
                    else -> "⬜"
                }
                val timeStr = if (time != null) "${time}s" else ""
                
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(text = status, modifier = Modifier.padding(end = 8.dp))
                        Text(text = stage)
                    }
                    if (timeStr.isNotEmpty()) {
                        Text(text = timeStr, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            val progress = if (isAnalyzing) 0.5f else 1.0f
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}
