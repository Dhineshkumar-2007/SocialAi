package com.socialai.app.features.problems

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.socialai.app.core.data.models.ProblemDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProblemListScreen(
    viewModel: ProblemListViewModel = hiltViewModel(),
    onNavigateToDetail: (Int) -> Unit,
    onNavigateToSubmit: () -> Unit,
    isCitizen: Boolean
) {
    val state by viewModel.state.collectAsState()
    var searchQuery by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf<String?>(null) }

    val categories = listOf("Water", "Healthcare", "Agriculture", "Education", "Environment", "Infrastructure", "Waste management", "Energy", "Transportation", "Employment")

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("Problems") },
                    actions = {
                        IconButton(onClick = { viewModel.loadProblems() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                        }
                    }
                )
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                    placeholder = { Text("Search problems...") },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) }
                )
                LazyRow(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(categories) { category ->
                        FilterChip(
                            selected = selectedCategory == category,
                            onClick = { selectedCategory = if (selectedCategory == category) null else category },
                            label = { Text(category) }
                        )
                    }
                }
            }
        },
        floatingActionButton = {
            if (isCitizen) {
                FloatingActionButton(onClick = onNavigateToSubmit) {
                    Icon(Icons.Default.Add, contentDescription = "Submit Problem")
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when (val currentState = state) {
                is ProblemListState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is ProblemListState.Success -> {
                    val filteredProblems = currentState.problems.filter {
                        (selectedCategory == null || it.category == selectedCategory) &&
                        (searchQuery.isBlank() || it.title.contains(searchQuery, ignoreCase = true))
                    }
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(filteredProblems) { problem ->
                            ProblemCard(problem = problem, onClick = { onNavigateToDetail(problem.id) })
                        }
                    }
                }
                is ProblemListState.Error -> {
                    Text(
                        text = currentState.message,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
            }
        }
    }
}

@Composable
fun ProblemCard(problem: ProblemDto, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = problem.title, style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AssistChip(onClick = {}, label = { Text(problem.category ?: "Uncategorized") })
                AssistChip(onClick = {}, label = { Text(problem.status) })
                AssistChip(onClick = {}, label = { Text(problem.priority ?: "Normal") })
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "District: ${problem.district ?: "Unknown"}", style = MaterialTheme.typography.bodySmall)
            Text(text = "Created: ${problem.createdAt}", style = MaterialTheme.typography.bodySmall)
        }
    }
}
