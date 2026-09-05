package com.socialai.app.features.problems

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

data class SubmitProblemState(
    val title: String = "",
    val description: String = "",
    val district: String = "",
    val lat: Double? = null,
    val lng: Double? = null,
    val evidenceUris: List<Uri> = emptyList(),
    val isSubmitting: Boolean = false,
    val error: String? = null,
    val submittedProblemId: Int? = null
)

@HiltViewModel
class SubmitProblemViewModel @Inject constructor(
    private val repository: ProblemRepository
) : ViewModel() {
    private val _state = MutableStateFlow(SubmitProblemState())
    val state: StateFlow<SubmitProblemState> = _state.asStateFlow()

    fun updateTitle(title: String) { _state.value = _state.value.copy(title = title) }
    fun updateDescription(desc: String) { _state.value = _state.value.copy(description = desc) }
    fun updateDistrict(district: String) { _state.value = _state.value.copy(district = district) }
    fun updateLocation(lat: Double, lng: Double) { _state.value = _state.value.copy(lat = lat, lng = lng) }
    fun addEvidenceUri(uri: Uri) { _state.value = _state.value.copy(evidenceUris = _state.value.evidenceUris + uri) }

    fun submitProblem(files: List<File>) {
        val currentState = _state.value
        _state.value = currentState.copy(isSubmitting = true, error = null)
        viewModelScope.launch {
            repository.submitProblem(
                title = currentState.title,
                description = currentState.description,
                district = currentState.district.takeIf { it.isNotBlank() },
                lat = currentState.lat,
                lng = currentState.lng,
                evidenceFiles = files
            ).fold(
                onSuccess = { response ->
                    _state.value = _state.value.copy(isSubmitting = false, submittedProblemId = response.id)
                },
                onFailure = { error ->
                    _state.value = _state.value.copy(isSubmitting = false, error = error.message)
                }
            )
        }
    }
}
