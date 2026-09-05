package com.socialai.app.features.problems

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.socialai.app.features.problems.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProblemDetailScreen(
    problemId: Int,
    viewModel: ProblemDetailViewModel = hiltViewModel()
) {
    val detailState by viewModel.detailState.collectAsState()
    val analysisState by viewModel.analysisState.collectAsState()
    val serverUrl = "http://10.0.2.2:5000"

    LaunchedEffect(problemId) {
        viewModel.loadProblem(problemId)
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Problem Details") }) }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when (val state = detailState) {
                is ProblemDetailState.Loading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                is ProblemDetailState.Error -> Text(state.message, color = MaterialTheme.colorScheme.error, modifier = Modifier.align(Alignment.Center))
                is ProblemDetailState.Success -> {
                    val problem = state.problem
                    val analysis = state.analysis

                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(text = problem.title, style = MaterialTheme.typography.headlineMedium)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            AssistChip(onClick = {}, label = { Text(problem.status) })
                            AssistChip(onClick = {}, label = { Text(problem.category ?: "Uncategorized") })
                            Text(text = problem.createdAt, style = MaterialTheme.typography.bodySmall, modifier = Modifier.align(Alignment.CenterVertically))
                        }
                        
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Text(text = problem.description, modifier = Modifier.padding(16.dp))
                        }

                        if (problem.status == "submitted" && analysis == null && analysisState !is AnalysisState.Analyzing) {
                            Button(onClick = { viewModel.triggerAnalysis(problem.id) }, modifier = Modifier.fillMaxWidth()) {
                                Text("Analyze with AI")
                            }
                        }

                        if (analysisState is AnalysisState.Analyzing) {
                            AiPipelineProgress(timings = emptyMap(), isAnalyzing = true)
                        }

                        analysis?.let { result ->
                            AiPipelineProgress(timings = result.timings ?: emptyMap(), isAnalyzing = false)
                            result.classification?.let { ClassificationCard(classification = it) }
                            result.evidenceAnalysis?.forEach { evidence ->
                                EvidenceVerificationCard(evidence = evidence, serverUrl = serverUrl)
                            }
                            if (!result.duplicates.isNullOrEmpty()) {
                                DuplicateClusterMap(duplicates = result.duplicates, currentProblem = problem)
                            }
                            result.priority?.let { PriorityBreakdownCard(priority = it) }
                            result.universityMatches?.forEachIndexed { index, match ->
                                UniversityMatchCard(match = match, rank = index + 1)
                            }
                            result.industryMatches?.forEach { match ->
                                IndustryMatchCard(match = match)
                            }
                        }
                    }
                }
            }
        }
    }
}
