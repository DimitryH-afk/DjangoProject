import datetime

from django.test import TestCase, SimpleTestCase, TransactionTestCase, LiveServerTestCase
from django.utils import timezone
from django.urls import reverse, resolve
from urllib.request import urlopen
from .models import Question, Choice


# Helper
def create_question(question_text, days):
    """
    Create a question with the given `question_text` and published the
    given number of `days` offset to now (negative for questions published
    in the past, positive for questions that have yet to be published).
    """
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


# TestCase: tests that use the database
class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is in the future.
        """
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is older than 1 day.
        """
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """
        was_published_recently() returns True for questions whose pub_date
        is within the last day.
        """
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


class QuestionIndexViewTests(TestCase):
    def test_no_questions(self):
        """
        If no questions exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        """
        Questions with a pub_date in the past are displayed on the index page.
        """
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_future_question(self):
        """
        Questions with a pub_date in the future aren't displayed on the index page.
        """
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_future_question_and_past_question(self):
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_two_past_questions(self):
        """
        The questions index page may display multiple questions.
        """
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question2, question1],
        )


class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:detail", args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text="Past question.", days=-5)
        url = reverse("polls:detail", args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)


# SimpleTestCase: no database, tests URLs and behaviour
class PollsURLTests(SimpleTestCase):
    def test_index_url_resolves(self):
        """
        The /polls/ URL should resolve to the index view.
        """
        resolver = resolve("/polls/")
        self.assertEqual(resolver.view_name, "polls:index")

    def test_index_url_reverse(self):
        """
        Reversing 'polls:index' should produce /polls/.
        """
        url = reverse("polls:index")
        self.assertEqual(url, "/polls/")


# TransactionTestCase — tests vote behaviour, real DB commits per operation
class VoteTransactionTests(TransactionTestCase):
    def test_voting_increments_choice_votes(self):
        """
        POSTing a valid vote increments the selected choice's vote count by 1.
        """
        question = create_question(question_text="Favourite colour?", days=-1)
        choice = question.choice_set.create(choice_text="Blue", votes=0)

        self.client.post(
            reverse("polls:vote", args=(question.id,)),
            {"choice": choice.id},
        )

        choice = Choice.objects.get(pk=choice.id)
        self.assertEqual(choice.votes, 1)

    def test_voting_with_no_choice_shows_error(self):
        """
        POSTing without selecting a choice re-renders the detail page with
        an error message.
        """
        question = create_question(question_text="Favourite colour?", days=-1)
        question.choice_set.create(choice_text="Blue", votes=0)

        response = self.client.post(
            reverse("polls:vote", args=(question.id,)),
            {},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You didn&#x27;t select a choice.")


# LiveServerTestCase — spins up a real HTTP server and makes a real request
class PollsLiveServerTests(LiveServerTestCase):
    def test_index_page_is_reachable(self):
        """
        The polls index page returns a 200 response over a real HTTP connection.
        """
        url = f"{self.live_server_url}/polls/"
        response = urlopen(url)
        self.assertEqual(response.status, 200)