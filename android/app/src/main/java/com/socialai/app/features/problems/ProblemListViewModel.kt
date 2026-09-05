package com.socialai.app.features.problems

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.socialai.app.core.data.models.ProblemDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class ProblemListState {
    object Loading : ProblemListState()
    data class Success(val problems: List<ProblemDto>) : ProblemListState()
    data class Error(val message: String) : ProblemListState()
}

@HiltViewModel
class ProblemListViewModel @Inject constructor(
    private val repository: ProblemRepository
) : ViewModel() {
    private val _state = MutableStateFlow<ProblemListState>(ProblemListState.Loading)
    val state: StateFlow<ProblemListState> = _state.asStateFlow()

    init {
        loadProblems()
    }

    fun loadProblems() {
        _state.value = ProblemListState.Loading
        viewModelScope.launch {
            repository.getProblems().fold(
                onSuccess = { problems ->
                    _state.value = ProblemListState.Success(problems)
                },
                onFailure = { error ->
                    _state.value = ProblemListState.Error(error.message ?: "Failed to load problems")
                }
            )
        }
    }
}
