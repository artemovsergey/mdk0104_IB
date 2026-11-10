using ConditionalPractice;

namespace ConditionalPractice.Tests;

public class GradeCalculatorTests
{
    [Theory]
    [InlineData(100, "A")]
    [InlineData(90, "A")]
    [InlineData(89, "B")]
    [InlineData(80, "B")]
    [InlineData(79, "C")]
    [InlineData(70, "C")]
    [InlineData(69, "D")]
    [InlineData(60, "D")]
    [InlineData(59, "F")]
    [InlineData(0, "F")]
    public void GetGrade_ReturnsExpected(int score, string expected)
    {
        Assert.Equal(expected, GradeCalculator.GetGrade(score));
    }

    [Theory]
    [InlineData(-1)]
    [InlineData(101)]
    public void GetGrade_ThrowsForOutOfRange(int score)
    {
        Assert.Throws<ArgumentOutOfRangeException>(
            () => GradeCalculator.GetGrade(score));
    }
}

public class ScoreInputTests
{
    [Theory]
    [InlineData("0", 0)]
    [InlineData("100", 100)]
    [InlineData(" 85 ", 85)]
    public void TryParse_AcceptsValid(string input, int expected)
    {
        Assert.True(ScoreInput.TryParse(input, out int score));
        Assert.Equal(expected, score);
    }

    [Theory]
    [InlineData("")]
    [InlineData(null)]
    [InlineData("abc")]
    [InlineData("101")]
    [InlineData("-5")]
    [InlineData("85.5")]
    public void TryParse_RejectsInvalid(string? input)
    {
        Assert.False(ScoreInput.TryParse(input, out _));
    }
}
