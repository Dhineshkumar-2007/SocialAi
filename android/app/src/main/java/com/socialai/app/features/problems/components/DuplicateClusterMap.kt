package com.socialai.app.features.problems.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.socialai.app.core.data.models.DuplicateResult
import com.socialai.app.core.data.models.ProblemDto

@Composable
fun DuplicateClusterMap(duplicates: List<DuplicateResult>, currentProblem: ProblemDto) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("🔗 Duplicate Detection", style = MaterialTheme.typography.titleLarge)
            Spacer(modifier = Modifier.height(8.dp))
            
            if (duplicates.isEmpty()) {
                Text("✅ No similar reports detected", color = Color.Green)
            } else {
                Text("Found ${duplicates.size} similar reports", style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(8.dp))
                
                duplicates.forEach { dup ->
                    Column(modifier = Modifier.padding(vertical = 4.dp)) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(text = "Problem ID: ${dup.duplicateId}", style = MaterialTheme.typography.bodySmall)
                            Text(text = "Score: ${(dup.similarityScore * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                        }
                        LinearProgressIndicator(
                            progress = { dup.similarityScore.toFloat() },
                            modifier = Modifier.fillMaxWidth()
                        )
                        Text(
                            text = "Semantic: ${(dup.semanticSimilarity * 100).toInt()}% | Geo dist: ${dup.geographicDistance}m",
                            style = MaterialTheme.typography.labelSmall
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                Text("Score = 0.80×semantic + 0.20×geographic", style = MaterialTheme.typography.labelSmall)
                Text("Threshold: 0.82", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}
