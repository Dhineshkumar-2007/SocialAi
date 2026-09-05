package com.socialai.app.features.problems

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import java.io.File
import java.io.FileOutputStream

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SubmitProblemScreen(
    viewModel: SubmitProblemViewModel = hiltViewModel(),
    onNavigateSuccess: (Int) -> Unit
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    
    LaunchedEffect(state.submittedProblemId) {
        state.submittedProblemId?.let { onNavigateSuccess(it) }
    }

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetMultipleContents()
    ) { uris -> uris.forEach { viewModel.addEvidenceUri(it) } }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Submit Problem") }) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = state.title,
                onValueChange = { viewModel.updateTitle(it) },
                label = { Text("Title") },
                modifier = Modifier.fillMaxWidth()
            )
            
            OutlinedTextField(
                value = state.description,
                onValueChange = { viewModel.updateDescription(it) },
                label = { Text("Description") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3
            )
            
            OutlinedTextField(
                value = state.district,
                onValueChange = { viewModel.updateDistrict(it) },
                label = { Text("District") },
                modifier = Modifier.fillMaxWidth()
            )
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = state.lat?.toString() ?: "",
                    onValueChange = { viewModel.updateLocation(it.toDoubleOrNull() ?: 0.0, state.lng ?: 0.0) },
                    label = { Text("Latitude") },
                    modifier = Modifier.weight(1f)
                )
                OutlinedTextField(
                    value = state.lng?.toString() ?: "",
                    onValueChange = { viewModel.updateLocation(state.lat ?: 0.0, it.toDoubleOrNull() ?: 0.0) },
                    label = { Text("Longitude") },
                    modifier = Modifier.weight(1f)
                )
            }
            
            Button(onClick = { galleryLauncher.launch("image/*") }) {
                Text("Add Photo Evidence")
            }
            Text("Photos selected: ${state.evidenceUris.size}")
            
            if (state.error != null) {
                Text(text = state.error!!, color = MaterialTheme.colorScheme.error)
            }
            
            Button(
                onClick = {
                    val files = state.evidenceUris.mapNotNull { uri ->
                        val inputStream = context.contentResolver.openInputStream(uri)
                        val tempFile = File(context.cacheDir, "evidence_${System.currentTimeMillis()}.jpg")
                        inputStream?.use { input ->
                            FileOutputStream(tempFile).use { output -> input.copyTo(output) }
                        }
                        tempFile.takeIf { it.exists() }
                    }
                    viewModel.submitProblem(files)
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !state.isSubmitting && state.title.isNotBlank() && state.description.isNotBlank()
            ) {
                if (state.isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                } else {
                    Text("Submit")
                }
            }
        }
    }
}
