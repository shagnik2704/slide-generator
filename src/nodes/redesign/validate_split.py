from src.nodes.redesign.utils.schema import SplitedTutorialList, SplitValidationResponse

def duration_test(duration: float):
    return 180 <= duration <= 240

def subtopic_test(number_of_tutorials: int, total_duration:float):
    expected = total_duration / 240     # expecting every subtopic to be 4 minutes
    return (expected - 1) <= number_of_tutorials <= (expected + 1)

def validate_tutorial_split(tutorial: SplitedTutorialList)->SplitValidationResponse:
    """
    Test for validating tutorial split responses.
    test cases:
    1. check whether subtopic duration is in range [180, 240] or not.
    2. check whether number of tutorials is in range [total_duration / 240 - 1, total_duration / 240 + 1] or not.
    """   
    validation_issues = []
    for subtopic in tutorial.tutorials:
        if not duration_test(subtopic.estimated_duration):
            validation_issues.append(f"Subtopic {subtopic.tutorial_title} has duration {subtopic.estimated_duration} which is not in range [180, 240]")

    if not subtopic_test(len(tutorial.tutorials), tutorial.total_duration):
        validation_issues.append(f"Number of tutorials {len(tutorial.tutorials)} is not in range [{tutorial.total_duration / 240 - 1}, {tutorial.total_duration / 240 + 1}]")

    return SplitValidationResponse(
        is_valid=len(validation_issues) == 0,
        issues=validation_issues
    )