package com.socialai.app.features.problems

import com.socialai.app.core.data.models.*
import com.socialai.app.core.network.ApiService
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import javax.inject.Inject

class ProblemRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getProblems(): Result<List<ProblemDto>> = try {
        Result.success(apiService.getProblems())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getProblem(id: Int): Result<ProblemDto> = try {
        Result.success(apiService.getProblem(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun submitProblem(
        title: String,
        description: String,
        district: String?,
        lat: Double?,
        lng: Double?,
        evidenceFiles: List<File>?
    ): Result<CreateProblemResponse> = try {
        val titleBody = title.toRequestBody("text/plain".toMediaTypeOrNull())
        val descBody = description.toRequestBody("text/plain".toMediaTypeOrNull())
        val districtBody = district?.toRequestBody("text/plain".toMediaTypeOrNull())
        val latBody = lat?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
        val lngBody = lng?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())

        val parts = evidenceFiles?.map { file ->
            val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
            MultipartBody.Part.createFormData("evidenceFiles", file.name, requestFile)
        }

        Result.success(apiService.submitProblem(titleBody, descBody, districtBody, latBody, lngBody, parts))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun analyzeProblem(id: Int): Result<AnalysisResponse> = try {
        Result.success(apiService.analyzeProblem(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getMatches(id: Int): Result<List<UniversityMatch>> = try {
        Result.success(apiService.getMatches(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getIndustryMatches(id: Int): Result<List<IndustryMatch>> = try {
        Result.success(apiService.getIndustryMatches(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun verifyResolution(problemId: Int, request: VerifyResolutionRequest): Result<VerifyResolutionResponse> = try {
        Result.success(apiService.verifyResolution(problemId, request))
    } catch (e: Exception) {
        Result.failure(e)
    }
}
