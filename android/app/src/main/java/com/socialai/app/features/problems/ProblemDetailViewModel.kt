package com.socialai.app.features.problems

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.socialai.app.core.data.models.AnalysisResponse
import com.socialai.app.core.data.models.ProblemDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class ProblemDetailState {
    object Loading : ProblemDetailState()
    data class Success(val problem: ProblemDto, val analysis: AnalysisResponse?) : ProblemDetailState()
    data class Error(val message: String) : ProblemDetailState()
}

sealed class AnalysisState {
    object Idle : AnalysisState()
    object Analyzing : AnalysisState()
    data class Complete(val result: AnalysisResponse) : AnalysisState()
    data class Error(val message: String) : AnalysisState()
}

@HiltViewModel
class ProblemDetailViewModel @Inject constructor(
    private val repository: ProblemRepository
) : ViewModel() {
    private val _detailState = MutableStateFlow<ProblemDetailState>(ProblemDetailState.Loading)
    val detailState: StateFlow<ProblemDetailState> = _detailState.asStateFlow()

    private val _analysisState = MutableStateFlow<AnalysisState>(AnalysisState.Idle)
    val analysisState: StateFlow<AnalysisState> = _analysisState.asStateFlow()

    fun loadProblem(id: Int) {
        _detailState.value = ProblemDetailState.Loading
        viewModelScope.launch {
            repository.getProblem(id).fold(
                onSuccess = { problem ->
                    _detailState.value = ProblemDetailState.Success(problem, null)
                },
                onFailure = { error ->
                    _detailState.value = ProblemDetailState.Error(error.message ?: "Error loading problem")
                }
            )
        }
    }

    fun triggerAnalysis(id: Int) {
        _analysisState.value = AnalysisState.Analyzing
        viewModelScope.launch {
            repository.analyzeProblem(id).fold(
                onSuccess = { analysis ->
                    _analysisState.value = AnalysisState.Complete(analysis)
                    val currentState = _detailState.value
                    if (currentState is ProblemDetailState.Success) {
                        _detailState.value = currentState.copy(analysis = analysis)
                    }
                },
                onFailure = { error ->
                    _analysisState.value = AnalysisState.Error(error.message ?: "Analysis failed")
                }
            )
        }
    }
}
